# app/ontology/turtle_serializer.py
"""
Serializes an rdflib Graph to Turtle and validates it before it is sent
anywhere. Validation here means the Turtle round-trips through rdflib's own
parser - SHACL/shape validation is explicitly out of scope.
"""

from rdflib import Graph

from app.ontology.exceptions import OntologyValidationError


class TurtleSerializer:
    def serialize(self, graph: Graph) -> str:
        turtle = graph.serialize(format="turtle")
        self._validate(turtle)
        return turtle

    @staticmethod
    def _validate(turtle: str) -> None:
        try:
            Graph().parse(data=turtle, format="turtle")
        except Exception as exc:
            raise OntologyValidationError(f"Generated Turtle failed to parse: {exc}") from exc
