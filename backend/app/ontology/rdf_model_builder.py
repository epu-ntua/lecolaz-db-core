# app/ontology/rdf_model_builder.py
"""
Builds an rdflib Graph from BIM domain DTOs, following the ontology mapping:

bim_datasets -> leco:BIMDataset
bim_storeys  -> leco:Storey
bim_spaces   -> leco:Space

leco:Storey and leco:Space are declared (in the ontology) as
rdfs:subClassOf bot:Storey / bot:Space (Building Topology Ontology), so
storey/space instances carry both types - a SPARQL query for either
leco:Storey or bot:Storey finds the same instance. leco:BIMDataset has no
BOT equivalent and stays leco-only. Likewise, storey->space containment
gets both leco:hasSpace and bot:hasSpace; dataset->storey stays
leco:hasStorey only (BOT has no direct dataset->storey property).

URIs for storeys/spaces are minted from their IFC GlobalId (stable across
re-parses of the same file), matching how IFC-derived entities are keyed
elsewhere in the ontology population design. The dataset itself has no
external identifier, so its URI is minted from the bim_dataset surrogate id.
"""

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, XSD

from app.ontology.config import ontology_settings
from app.ontology.dto import BimDatasetDTO

BOT = Namespace("https://w3id.org/bot#")


class RdfModelBuilder:
    def __init__(self, namespace: str | None = None) -> None:
        self._leco = Namespace(namespace or ontology_settings.LECO_NAMESPACE)

    def build(self, bim: BimDatasetDTO) -> Graph:
        graph = Graph()
        graph.bind("leco", self._leco)
        graph.bind("bot", BOT)
        graph.bind("dct", DCTERMS)
        graph.bind("xsd", XSD)
        graph.bind("rdfs", RDFS)

        dataset_uri = self._dataset_uri(bim.bim_dataset_id)
        self._add_dataset_triples(graph, dataset_uri, bim)

        storey_uri_by_id: dict = {}
        for storey in bim.storeys:
            storey_uri = self._storey_uri(storey.global_id)
            storey_uri_by_id[storey.id] = storey_uri
            self._add_storey_triples(graph, storey_uri, storey)
            graph.add((dataset_uri, self._leco.hasStorey, storey_uri))

        for space in bim.spaces:
            space_uri = self._space_uri(space.global_id)
            self._add_space_triples(graph, space_uri, space)

            parent_storey_uri = storey_uri_by_id.get(space.storey_id)
            if parent_storey_uri is not None:
                graph.add((parent_storey_uri, self._leco.hasSpace, space_uri))
                graph.add((parent_storey_uri, BOT.hasSpace, space_uri))
            else:
                graph.add((dataset_uri, self._leco.hasSpace, space_uri))

        return graph

    def _add_dataset_triples(self, graph: Graph, dataset_uri: URIRef, bim: BimDatasetDTO) -> None:
        graph.add((dataset_uri, RDF.type, self._leco.BIMDataset))
        graph.add((dataset_uri, self._leco.hasIdentifier, Literal(str(bim.bim_dataset_id))))
        if bim.format:
            graph.add((dataset_uri, self._leco.hasFileFormat, Literal(bim.format)))
        if bim.status:
            graph.add((dataset_uri, self._leco.hasStatus, Literal(bim.status)))
        if bim.created_at is not None:
            graph.add(
                (dataset_uri, self._leco.hasUploadDate, Literal(bim.created_at, datatype=XSD.dateTime))
            )
        if bim.filename:
            graph.add((dataset_uri, DCTERMS.title, Literal(bim.filename)))
        if bim.size_bytes is not None:
            graph.add(
                (dataset_uri, self._leco.hasSize, Literal(bim.size_bytes, datatype=XSD.decimal))
            )

    def _add_storey_triples(self, graph: Graph, storey_uri: URIRef, storey) -> None:
        graph.add((storey_uri, RDF.type, self._leco.Storey))
        graph.add((storey_uri, RDF.type, BOT.Storey))
        graph.add((storey_uri, self._leco.hasIdentifier, Literal(str(storey.id))))
        graph.add((storey_uri, self._leco.hasGlobalId, Literal(storey.global_id)))
        if storey.name:
            graph.add((storey_uri, RDFS.label, Literal(storey.name)))
        if storey.elevation is not None:
            graph.add(
                (storey_uri, self._leco.hasLevel, Literal(storey.elevation, datatype=XSD.decimal))
            )

    def _add_space_triples(self, graph: Graph, space_uri: URIRef, space) -> None:
        graph.add((space_uri, RDF.type, self._leco.Space))
        graph.add((space_uri, RDF.type, BOT.Space))
        graph.add((space_uri, self._leco.hasIdentifier, Literal(str(space.id))))
        graph.add((space_uri, self._leco.hasGlobalId, Literal(space.global_id)))
        if space.name:
            graph.add((space_uri, RDFS.label, Literal(space.name)))
        if space.area is not None:
            graph.add((space_uri, self._leco.hasArea, Literal(space.area, datatype=XSD.decimal)))
        if space.volume is not None:
            graph.add((space_uri, self._leco.hasVolume, Literal(space.volume, datatype=XSD.decimal)))

    def _dataset_uri(self, bim_dataset_id) -> URIRef:
        return URIRef(f"{self._leco}bim-dataset-{bim_dataset_id}")

    def _storey_uri(self, global_id: str) -> URIRef:
        return URIRef(f"{self._leco}storey-{global_id}")

    def _space_uri(self, global_id: str) -> URIRef:
        return URIRef(f"{self._leco}space-{global_id}")
