# app/ontology/rdf_model_builder.py
"""
Builds an rdflib Graph from BIM domain DTOs, following the ontology mapping:

bim_datasets -> leco:BIMDataset, leco:Building
bim_storeys  -> leco:Storey
bim_spaces   -> leco:Space

BIMDataset instances are also typed leco:Dataset (its superclass), since
Fuseki runs without inference.

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

Simulation (EnergyPlus ESO) mapping, build_simulation():

simulation_datasets  -> leco:EnergyModelDataset (+ leco:Dataset) and one
                        leco:SimulationRun
simulation_variables -> leco:Observation (+ sosa:Observation), only for
                        variable names listed in ESO_VARIABLE_CONCEPTS
                        (the rest stay in Postgres only)

    SimulationRun leco:usesEnergyModelDataset EnergyModelDataset
    SimulationRun leco:simulates              <ObservableProperty concept>
    Observation   sosa:observedProperty       <ObservableProperty concept>
    Observation   sosa:hasFeatureOfInterest   Space (when the zone matched a BIM space)
    Observation   leco:timeSeriesRef          API URL returning its timeseries
                                              (GET /simulations/{id}/timeseries)

Timeseries values stay in Postgres. No Observation -> SimulationRun link is
emitted (the schema has none); the simulation's named graph gives provenance.
Units are not emitted: leco:hasUnit's domain is the shared concept, not the
variable. Observation URIs are keyed by simulation_dataset id + ESO variable
id, so they are stable across reprocessing.
"""

from pathlib import PurePath

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, XSD

from app.core.config import settings
from app.ontology.dto import BimDatasetDTO, SimulationDatasetDTO

BOT = Namespace("https://w3id.org/bot#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")

# EnergyPlus ESO variable name -> local name of a leco:ObservableProperty
# individual declared in the ontology schema. Only unambiguous matches.
ESO_VARIABLE_CONCEPTS = {
    "Zone Mean Air Temperature": "IndoorAirTemperature",
    "Zone Air Relative Humidity": "RelativeHumidity",
    "Zone Ideal Loads Supply Air Total Heating Energy": "EnergyConsumption",
    "Zone Ideal Loads Supply Air Total Cooling Energy": "EnergyConsumption",
}


class RdfModelBuilder:
    def __init__(self, namespace: str | None = None, api_base_url: str | None = None) -> None:
        self._leco = Namespace(namespace or settings.LECO_NAMESPACE)
        self._api_base_url = (api_base_url or settings.API_PUBLIC_BASE_URL).rstrip("/")

    def build(self, bim: BimDatasetDTO) -> Graph:
        graph = Graph()
        graph.bind("leco", self._leco)
        graph.bind("bot", BOT)
        graph.bind("dct", DCTERMS)
        graph.bind("xsd", XSD)
        graph.bind("rdfs", RDFS)

        dataset_uri = self._dataset_uri(bim.bim_dataset_id)
        self._add_dataset_triples(
            graph, dataset_uri, self._leco.BIMDataset, bim.bim_dataset_id, bim
        )

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

    def build_simulation(self, sim: SimulationDatasetDTO) -> Graph:
        graph = Graph()
        graph.bind("leco", self._leco)
        graph.bind("sosa", SOSA)
        graph.bind("dct", DCTERMS)
        graph.bind("xsd", XSD)
        graph.bind("rdfs", RDFS)

        dataset_uri = self._energy_model_dataset_uri(sim.simulation_dataset_id)
        self._add_dataset_triples(
            graph, dataset_uri, self._leco.EnergyModelDataset, sim.simulation_dataset_id, sim
        )

        run_uri = self._simulation_run_uri(sim.simulation_dataset_id)
        graph.add((run_uri, RDF.type, self._leco.SimulationRun))
        graph.add((run_uri, self._leco.usesEnergyModelDataset, dataset_uri))

        for variable in sim.variables:
            concept = ESO_VARIABLE_CONCEPTS.get(variable.variable_name)
            if concept is None:
                continue
            concept_uri = self._leco[concept]
            graph.add((run_uri, self._leco.simulates, concept_uri))

            observation_uri = self._observation_uri(sim.simulation_dataset_id, variable.variable_id)
            self._add_observation_triples(
                graph, observation_uri, sim.simulation_dataset_id, variable, concept_uri
            )

        return graph

    def _add_dataset_triples(
        self, graph: Graph, dataset_uri: URIRef, dataset_class: URIRef, identifier, dataset
    ) -> None:
        graph.add((dataset_uri, RDF.type, dataset_class))
        graph.add((dataset_uri, RDF.type, self._leco.Dataset))
        graph.add((dataset_uri, self._leco.hasIdentifier, Literal(str(identifier))))
        if dataset.format:
            graph.add((dataset_uri, self._leco.hasFileFormat, Literal(dataset.format)))
        if dataset.status:
            graph.add((dataset_uri, self._leco.hasStatus, Literal(dataset.status)))
        if dataset.created_at is not None:
            graph.add(
                (dataset_uri, self._leco.hasUploadDate, Literal(dataset.created_at, datatype=XSD.dateTime))
            )
        if dataset.filename:
            graph.add((dataset_uri, DCTERMS.title, Literal(dataset.filename)))
        if dataset.size_bytes is not None:
            graph.add(
                (dataset_uri, self._leco.hasSize, Literal(dataset.size_bytes, datatype=XSD.decimal))
            )

    def _add_observation_triples(
        self, graph: Graph, observation_uri: URIRef, simulation_dataset_id, variable, concept_uri: URIRef
    ) -> None:
        graph.add((observation_uri, RDF.type, self._leco.Observation))
        graph.add((observation_uri, RDF.type, SOSA.Observation))
        graph.add((observation_uri, self._leco.hasIdentifier, Literal(str(variable.id))))
        label = f"{variable.variable_name} ({variable.key})" if variable.key else variable.variable_name
        graph.add((observation_uri, RDFS.label, Literal(label)))
        graph.add((observation_uri, SOSA.observedProperty, concept_uri))
        if variable.space_global_id:
            graph.add(
                (observation_uri, SOSA.hasFeatureOfInterest, self._space_uri(variable.space_global_id))
            )
        graph.add(
            (
                observation_uri,
                self._leco.timeSeriesRef,
                Literal(self._timeseries_ref(simulation_dataset_id, variable.id), datatype=XSD.anyURI),
            )
        )

    def _add_building_triples(self, graph: Graph, building_uri: URIRef, bim: BimDatasetDTO) -> None:
        # TODO: building information (IfcBuilding) exists in the BIM file but is
        # not yet stored in the DB, so the Building is derived from the dataset
        # filename. Marked for future work.
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

    def _energy_model_dataset_uri(self, simulation_dataset_id) -> URIRef:
        return URIRef(f"{self._leco}energy-model-dataset-{simulation_dataset_id}")

    def _simulation_run_uri(self, simulation_dataset_id) -> URIRef:
        return URIRef(f"{self._leco}simulation-run-{simulation_dataset_id}")

    def _observation_uri(self, simulation_dataset_id, eso_variable_id: str) -> URIRef:
        return URIRef(f"{self._leco}simulation-observation-{simulation_dataset_id}-{eso_variable_id}")

    def _timeseries_ref(self, simulation_dataset_id, simulation_variable_id) -> str:
        # app/api/simulations.py: list_simulation_timeseries
        return (
            f"{self._api_base_url}/simulations/{simulation_dataset_id}/timeseries"
            f"?variable_id={simulation_variable_id}"
        )
