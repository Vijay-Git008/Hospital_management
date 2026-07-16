import datetime
import json
from sqlalchemy.orm import Session
from ..db.models import Resource, Patient, Incident, Negotiation, NegotiationStep, Allocation, AuditRecord
from ..agents.case_agent import CaseAgent
from ..agents.resource_agents import ResourceAgent
from .dependency_graph import ResourceDependencyGraph
from .scoring import calculate_priority_score
from ..ai.explainer import explain_allocation, summarize_incident

# We will hook the ws hub in main.py to avoid circular dependencies
class NegotiationEngine:
    def __init__(self, broadcast_callback=None):
        self.broadcast_callback = broadcast_callback

    async def run_negotiation_cycle(self, db: Session, incident_id: str):
        """
        Runs a full multi-agent CNP negotiation cycle for an active incident.
        Resolves resource conflicts deterministically and explains them.
        """
        # Load incident
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return

        # Load pending patients under this incident
        pending_patients = db.query(Patient).filter(
            Patient.status == "Pending"
        ).all()

        if not pending_patients:
            return

        # Load resources and allocations
        resources = db.query(Resource).all()
        active_allocations = db.query(Allocation).filter(Allocation.status == "Active").all()

        # Format resources & allocations for graph processing
        resources_list = []
        for r in resources:
            resources_list.append({
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "status": r.status,
                "metadata": json.loads(r.metadata_json)
            })

        allocs_list = []
        for a in active_allocations:
            allocs_list.append({
                "resource_id": a.resource_id,
                "patient_id": a.patient_id
            })

        pending_cases_list = []
        for p in pending_patients:
            clinical = json.loads(p.clinical_data_json)
            pending_cases_list.append({
                "id": p.id,
                "name": p.name_encrypted,  # pseudo encrypted name
                "triage_level": p.triage_level,
                "status": p.status,
                "required_resource_types": clinical.get("required_resources", [])
            })

        # Update dependency graph topology
        dep_graph = ResourceDependencyGraph()
        dep_graph.update_topology(resources_list, allocs_list, pending_cases_list)

        # 1. Initialize Case Agents and trigger Call for Proposals (CFP)
        negotiation_records = []
        patient_bids = {}  # patient_id -> list of bids

        for p in pending_patients:
            clinical = json.loads(p.clinical_data_json)
            required_types = clinical.get("required_resources", [])

            # Create Case Agent
            case_agent = CaseAgent(
                patient_id=p.id,
                name=p.name_encrypted,
                triage_level=p.triage_level,
                required_resource_types=required_types,
                clinical_summary=clinical.get("summary", "Emergency Admission")
            )

            # Create Negotiation Record
            negotiation = Negotiation(
                incident_id=incident_id,
                patient_id=p.id,
                status="Bidding",
                reasoning_tree_json="{}"
            )
            db.add(negotiation)
            db.flush()  # gets negotiation ID

            # Record CFP Step
            cfp_msg = case_agent.generate_cfp()
            step_cfp = NegotiationStep(
                negotiation_id=negotiation.id,
                step_type="CFP",
                agent_id=p.id,
                content_json=json.dumps(cfp_msg.payload)
            )
            db.add(step_cfp)

            patient_bids[p.id] = {
                "negotiation_id": negotiation.id,
                "negotiation": negotiation,
                "case_agent": case_agent,
                "bids": []
            }

            # 2. Resource Bidding (Supply side agents evaluate CFP)
            for r in resources:
                meta = json.loads(r.metadata_json)
                res_agent = ResourceAgent(
                    resource_id=r.id,
                    name=r.name,
                    resource_type=r.type,
                    status=r.status,
                    metadata=meta
                )

                bid = res_agent.calculate_bid(cfp_msg)
                if bid:
                    # Calculate downstream impacts in case we lock this resource
                    impacts = dep_graph.get_cascading_impacts(r.id)
                    impact_count = len(impacts)

                    # Triage wait time
                    waiting_minutes = (datetime.datetime.utcnow() - p.admission_time).total_seconds() / 60.0

                    # Calculate multi-criteria scoring
                    suitability = bid.payload["suitability_score"]
                    scoring_res = calculate_priority_score(
                        triage_level=p.triage_level,
                        waiting_time_minutes=waiting_minutes,
                        suitability_score=suitability,
                        downstream_impact_count=impact_count
                    )

                    score = scoring_res["total_score"]

                    # Append to bids
                    patient_bids[p.id]["bids"].append({
                        "resource_id": r.id,
                        "resource_name": r.name,
                        "resource_type": r.type,
                        "suitability_score": suitability,
                        "downstream_impacts": [imp["name"] for imp in impacts],
                        "scoring": scoring_res,
                        "total_score": score
                    })

                    # Record BID Step
                    step_bid = NegotiationStep(
                        negotiation_id=negotiation.id,
                        step_type="BID",
                        agent_id=r.id,
                        content_json=json.dumps({
                            "bid_score": score,
                            "suitability": suitability,
                            "impact_count": impact_count,
                            "breakdown": scoring_res
                        })
                    )
                    db.add(step_bid)

        # 3. Conflict Resolution & Resource Allocation
        # Flatten all resource bids to find conflicts (same resource bid on by multiple patients)
        # Sort patients by their average bid score (or highest bid score) to allocate deterministically
        patient_priorities = []
        for pid, data in patient_bids.items():
            bids = data["bids"]
            if not bids:
                avg_score = 0.0
            else:
                avg_score = sum(b["total_score"] for b in bids) / len(bids)
            patient_priorities.append((pid, avg_score))

        # Sort patient priorities descending by score
        patient_priorities.sort(key=lambda x: x[1], reverse=True)

        allocated_resource_ids = set()

        for patient_id, avg_score in patient_priorities:
            p_data = patient_bids[patient_id]
            negotiation = p_data["negotiation"]
            required_types = p_data["case_agent"].required_resource_types

            # We need to satisfy the full resource bundle for the patient
            # Find the highest scoring available resource of each required type
            selected_resources = []
            satisfied = True

            for req_type in required_types:
                # Find all bids for this resource type that are not yet allocated in this cycle
                valid_bids = [
                    b for b in p_data["bids"]
                    if b["resource_type"] == req_type and b["resource_id"] not in allocated_resource_ids
                ]

                # Sort by score descending
                valid_bids.sort(key=lambda x: x["total_score"], reverse=True)

                if valid_bids:
                    # Pick highest scoring resource
                    selected_resources.append(valid_bids[0])
                else:
                    satisfied = False
                    break

            # If the complete bundle is satisfied, allocate resources
            if satisfied and selected_resources:
                # Record successful award
                negotiation.status = "Awarded"
                reasoning_tree = {
                    "average_negotiation_score": avg_score,
                    "allocated_bundle": selected_resources,
                    "resolution": "Deterministic priority bundle resolution succeeded."
                }
                
                # Fetch patient object
                patient = db.query(Patient).filter(Patient.id == patient_id).first()
                patient.status = "Allocated"

                # Allocate resources in DB
                for res_info in selected_resources:
                    res_id = res_info["resource_id"]
                    allocated_resource_ids.add(res_id)

                    # Update resource status
                    res = db.query(Resource).filter(Resource.id == res_id).first()
                    res.status = "Occupied"

                    # Checksum chaining
                    prev_alloc = db.query(Allocation).filter(Allocation.status == "Active").order_by(Allocation.created_at.desc()).first()
                    prev_checksum = prev_alloc.checksum if prev_alloc else ""

                    alloc = Allocation(
                        negotiation_id=negotiation.id,
                        resource_id=res_id,
                        patient_id=patient_id,
                        status="Active",
                        checksum=""
                    )
                    db.add(alloc)
                    db.flush()  # gets ID

                    # Write cryptographic checksum
                    alloc.checksum = alloc.calculate_checksum(prev_checksum)

                    # Record Award Step
                    step_award = NegotiationStep(
                        negotiation_id=negotiation.id,
                        step_type="AWARD",
                        agent_id=res_id,
                        content_json=json.dumps(res_info)
                    )
                    db.add(step_award)

                # Generate AI Narrative Explanation
                patient_info = {
                    "triage_level": patient.triage_level,
                    "summary": json.loads(patient.clinical_data_json).get("summary", ""),
                    "waiting_time_minutes": round((datetime.datetime.utcnow() - patient.admission_time).total_seconds() / 60.0, 1)
                }

                # Compile explanation info
                downstream_impacts = []
                for res_info in selected_resources:
                    downstream_impacts.extend(res_info.get("downstream_impacts", []))

                explanation = await explain_allocation(
                    db=db,
                    patient_info=patient_info,
                    allocation_info=[{"resource": r["resource_name"], "type": r["resource_type"]} for r in selected_resources],
                    scoring_details={"average_score": avg_score, "bundle_details": selected_resources},
                    downstream_impacts=list(set(downstream_impacts))
                )

                reasoning_tree["ai_narrative"] = explanation
                negotiation.reasoning_tree_json = json.dumps(reasoning_tree)

                # Write Audit Record
                prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
                prev_checksum_audit = prev_audit.checksum if prev_audit else ""
                
                audit = AuditRecord(
                    user_id=None,  # system operation
                    action="AutomatedAllocation",
                    target_id=patient_id,
                    payload_json=json.dumps({"allocated_resources": [r["resource_id"] for r in selected_resources], "score": avg_score}),
                    ip_address="127.0.0.1",
                    checksum=""
                )
                db.add(audit)
                db.flush()
                audit.checksum = audit.calculate_checksum(prev_checksum_audit)

            else:
                # Negotiation failed or could not satisfy the resource bundle
                negotiation.status = "Failed"
                negotiation.reasoning_tree_json = json.dumps({
                    "average_score": avg_score,
                    "resolution": "Could not satisfy complete bundle requirements. Patient remains in queue."
                })

                # Record Reject Steps for resources bid on
                for bid_info in p_data["bids"]:
                    step_reject = NegotiationStep(
                        negotiation_id=negotiation.id,
                        step_type="REJECT",
                        agent_id=bid_info["resource_id"],
                        content_json=json.dumps({
                            "reason": "Complete resource bundle cannot be resolved at this priority level."
                        })
                    )
                    db.add(step_reject)

        db.commit()

        # Update and notify topology via WebSocket callback
        if self.broadcast_callback:
            # Gather fresh graph serialization
            all_res = db.query(Resource).all()
            res_json = [{"id": r.id, "name": r.name, "type": r.type, "status": r.status, "metadata": json.loads(r.metadata_json)} for r in all_res]

            all_allocs = db.query(Allocation).filter(Allocation.status == "Active").all()
            allocs_json = [{"resource_id": a.resource_id, "patient_id": a.patient_id} for a in all_allocs]

            all_cases = db.query(Patient).all()
            cases_json = [{"id": c.id, "name": c.name_encrypted, "triage_level": c.triage_level, "status": c.status, "required_resource_types": json.loads(c.clinical_data_json).get("required_resources", [])} for c in all_cases]

            new_graph = ResourceDependencyGraph()
            new_graph.update_topology(res_json, allocs_json, cases_json)
            graph_data = new_graph.get_serialization_data()

            await self.broadcast_callback({
                "event": "negotiation_complete",
                "incident_id": incident_id,
                "graph": graph_data
            })
