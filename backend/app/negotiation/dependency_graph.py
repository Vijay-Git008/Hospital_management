import networkx as nx

class ResourceDependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def update_topology(self, resources: list, active_allocations: list, pending_cases: list):
        """Rebuilds the dependency graph based on current network state."""
        self.graph.clear()

        # Add all resources as nodes
        for r in resources:
            self.graph.add_node(
                r["id"],
                type="resource",
                name=r["name"],
                res_type=r["type"],
                status=r["status"]
            )

        # Add all pending patient cases as nodes
        for p in pending_cases:
            self.graph.add_node(
                p["id"],
                type="patient",
                triage=p["triage_level"],
                status=p["status"]
            )
            # Add edge: Patient requires this resource
            for req in p.get("required_resource_types", []):
                # Search for resources matching this type and connect them
                matching_res = [r for r in resources if r["type"] == req]
                for mr in matching_res:
                    self.graph.add_edge(p["id"], mr["id"], relationship="requires")

        # Add active allocations as directed edges (resource allocated to patient)
        for alloc in active_allocations:
            # Connect resource node to patient node
            res_id = alloc["resource_id"]
            pat_id = alloc["patient_id"]
            if self.graph.has_node(res_id) and self.graph.has_node(pat_id):
                self.graph.add_edge(res_id, pat_id, relationship="allocated")

    def get_cascading_impacts(self, target_resource_id: str) -> list:
        """
        Calculates downstream impacts using depth-first search on locked resources.
        If a resource is locked, what cases and sub-resources are affected?
        """
        if not self.graph.has_node(target_resource_id):
            return []

        # Find all reachable nodes from target_resource_id
        # In a directed graph, if resource is allocated to Patient A,
        # then Patient A might hold dependencies that lock other resources.
        impacted_nodes = []
        visited = set()
        
        # Simple DFS/BFS traversal to find downstream nodes
        queue = [target_resource_id]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            
            # Skip target node in the output
            if curr != target_resource_id:
                node_data = self.graph.nodes[curr]
                impacted_nodes.append({
                    "id": curr,
                    "name": node_data.get("name", f"Patient {curr[:8]}"),
                    "type": node_data.get("type"),
                    "details": node_data
                })
            
            # Add neighbors (outgoing edges)
            for neighbor in self.graph.neighbors(curr):
                queue.append(neighbor)
                
        return impacted_nodes

    def get_serialization_data(self) -> dict:
        """Converts graph into format readable by React Flow (Nodes and Edges)."""
        nodes = []
        edges = []

        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "data": {
                    "label": data.get("name", f"Case {node_id[:8]}"),
                    "type": data.get("type"),
                    "res_type": data.get("res_type", "Triage Case"),
                    "status": data.get("status", "Pending")
                },
                "position": {"x": 0, "y": 0}  # Positioned dynamically by layout engine in UI
            })

        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "id": f"edge-{u}-{v}",
                "source": u,
                "target": v,
                "label": data.get("relationship", "dependency"),
                "animated": data.get("relationship") == "allocated"
            })

        return {"nodes": nodes, "edges": edges}
