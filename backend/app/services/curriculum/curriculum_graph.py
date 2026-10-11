"""
app/services/curriculum/curriculum_graph.py — Dependency-Aware Progression

Uses a Directed Acyclic Graph (DAG) to map skill dependencies. 
Ensures multiple learning paths and strict prerequisite enforcement.
"""

from typing import List, Dict, Any, Set

# Nodes represent distinct concepts, items, or stroke patterns.
# Value is a list of prerequisites (parent nodes).
CURRICULUM_DAG: Dict[str, List[str]] = {
    # Stroke Primitives
    "straight_lines": [],
    "curved_lines": ["straight_lines"],
    "complex_shapes": ["straight_lines", "curved_lines"],

    # Letter Groups
    "angular_caps": ["straight_lines"],           # A, E, F, H, I, L, M, N, T, V, W, X, Y, Z
    "curved_caps": ["curved_lines"],              # C, O, S
    "mixed_caps": ["angular_caps", "curved_caps"],# B, D, G, J, P, Q, R, U

    # Spelling Primitives
    "cvc_basics": ["angular_caps", "curved_caps"],
    "complex_words": ["cvc_basics", "mixed_caps"],
    
    # Specific Word Constraints (dynamic resolution possible)
    "word_CAT": ["cvc_basics"],
    "word_APPLE": ["complex_words"]
}

class CurriculumGraph:
    def __init__(self, dag: Dict[str, List[str]] = CURRICULUM_DAG):
        self.dag = dag

    def get_prerequisites(self, node: str) -> List[str]:
        """Returns immediate prerequisites for a node."""
        return self.dag.get(node, [])

    def get_all_ancestors(self, node: str) -> Set[str]:
        """Recursively resolves all dependencies for a given node."""
        ancestors = set()
        stack = [node]
        
        while stack:
            current = stack.pop()
            parents = self.dag.get(current, [])
            for p in parents:
                if p not in ancestors:
                    ancestors.add(p)
                    stack.append(p)
                    
        return ancestors

    def can_unlock(self, node: str, mastered_nodes: Set[str]) -> bool:
        """
        Checks if a node can be unlocked based on the user's mastered nodes.
        Requires all immediate prerequisites to be mastered.
        """
        reqs = self.get_prerequisites(node)
        return all(r in mastered_nodes for r in reqs)

    def get_available_nodes(self, mastered_nodes: Set[str]) -> List[str]:
        """Returns all nodes that have their prerequisites met but aren't mastered yet."""
        available = []
        for node in self.dag.keys():
            if node not in mastered_nodes and self.can_unlock(node, mastered_nodes):
                available.append(node)
        return available
