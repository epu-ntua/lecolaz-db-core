# app/ontology/rdf_model_builder.py
"""
Builds an rdflib Graph from BIM domain DTOs, following the ontology mapping:

bim_datasets -> leco:BIMDataset, leco:Building
bim_storeys  -> leco:Storey
bim_spaces   -> leco:Space

Building/Storey/Space instances are typed as both leco: and bot: classes
(leco:Building/Storey/Space are rdfs:subClassOf bot:Building/Storey/Space).

Buildings are not stored in Postgres: one Building is derived per BIM
dataset, labelled with the filename (extension stripped). Every storey of
the dataset is assigned to it, i.e. one building per IFC file is assumed.

Relations:
    BIMDataset leco:describesBuilding Building
    Building bot:hasStorey Storey           (spatial containment)
    Storey bot:hasSpace Space               (spatial containment)
    BIMDataset leco:containsSpace Space     (file membership, not spatial)
    BIMDataset leco:containsStorey Storey   (file membership, not spatial)

leco:hasElevation = bim_storeys.elevation, in IFC project length units
(no conversion). leco:hasLevel / leco:hasFloorHeight are not emitted:
IFC provides no reliable source for them.

URIs: storeys/spaces from IFC GlobalId (stable across re-parses);
dataset and building from the bim_dataset id.
"""

from pathlib import PurePath

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, XSD

from app.core.config import settings
from app.ontology.dto import BimDatasetDTO

BOT = Namespace("https://w3id.org/bot#")


class RdfModelBuilder:
    def __init__(self, namespace: str | None = None) -> None:
        self._leco = Namespace(namespace or settings.LECO_NAMESPACE)

    def build(self, bim: BimDatasetDTO) -> Graph:
        graph = Graph()
        graph.bind("leco", self._leco)
        graph.bind("bot", BOT)
        graph.bind("dct", DCTERMS)
        graph.bind("xsd", XSD)
        graph.bind("rdfs", RDFS)

        dataset_uri = self._dataset_uri(bim.bim_dataset_id)
        self._add_dataset_triples(graph, dataset_uri, bim)

        building_uri = self._building_uri(bim.bim_dataset_id)
        self._add_building_triples(graph, building_uri, bim)
        graph.add((dataset_uri, self._leco.describesBuilding, building_uri))

        storey_uri_by_id: dict = {}
        for storey in bim.storeys:
            storey_uri = self._storey_uri(storey.global_id)
            storey_uri_by_id[storey.id] = storey_uri
            self._add_storey_triples(graph, storey_uri, storey)
            graph.add((dataset_uri, self._leco.containsStorey, storey_uri))
            graph.add((building_uri, BOT.hasStorey, storey_uri))

        for space in bim.spaces:
            space_uri = self._space_uri(space.global_id)
            self._add_space_triples(graph, space_uri, space)
            graph.add((dataset_uri, self._leco.containsSpace, space_uri))

            parent_storey_uri = storey_uri_by_id.get(space.storey_id)
            if parent_storey_uri is not None:
                graph.add((parent_storey_uri, BOT.hasSpace, space_uri))

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

    def _add_building_triples(self, graph: Graph, building_uri: URIRef, bim: BimDatasetDTO) -> None:
        graph.add((building_uri, RDF.type, self._leco.Building))
        graph.add((building_uri, RDF.type, BOT.Building))
        if bim.filename:
            graph.add((building_uri, RDFS.label, Literal(PurePath(bim.filename).stem)))

    def _add_storey_triples(self, graph: Graph, storey_uri: URIRef, storey) -> None:
        graph.add((storey_uri, RDF.type, self._leco.Storey))
        graph.add((storey_uri, RDF.type, BOT.Storey))
        graph.add((storey_uri, self._leco.hasIdentifier, Literal(str(storey.id))))
        graph.add((storey_uri, self._leco.hasGlobalId, Literal(storey.global_id)))
        if storey.name:
            graph.add((storey_uri, RDFS.label, Literal(storey.name)))
        if storey.elevation is not None:
            graph.add(
                (storey_uri, self._leco.hasElevation, Literal(storey.elevation, datatype=XSD.decimal))
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

    def _building_uri(self, bim_dataset_id) -> URIRef:
        return URIRef(f"{self._leco}building-{bim_dataset_id}")

    def _storey_uri(self, global_id: str) -> URIRef:
        return URIRef(f"{self._leco}storey-{global_id}")

    def _space_uri(self, global_id: str) -> URIRef:
        return URIRef(f"{self._leco}space-{global_id}")
