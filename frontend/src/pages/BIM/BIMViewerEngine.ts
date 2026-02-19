import * as OBC from "@thatopen/components";

export class BIMViewerEngine {
  private components: OBC.Components;
  private world: OBC.World;
  private fragments: OBC.FragmentsManager;
  private ifcLoader: OBC.IfcLoader;

  constructor(container: HTMLElement) {
    this.components = new OBC.Components();

    const worlds = this.components.get(OBC.Worlds);
    const world = worlds.create<OBC.SimpleScene, OBC.SimpleCamera, OBC.SimpleRenderer>();
    if (!world) throw new Error("Failed to create world");
    this.world = world;

    this.world.scene = new OBC.SimpleScene(this.components);
    this.world.renderer = new OBC.SimpleRenderer(this.components, container);
    this.world.camera = new OBC.SimpleCamera(this.components);

    this.components.init();

    this.world.scene.setup();
  }

  async initIfcPipeline() {
    this.fragments = this.components.get(OBC.FragmentsManager);
    this.ifcLoader = this.components.get(OBC.IfcLoader);

    // 1️⃣ Init fragments worker FIRST
    const workerSrc =
      "https://thatopen.github.io/engine_fragment/resources/worker.mjs";
    const fetched = await fetch(workerSrc);
    if (!fetched.ok) throw new Error("Failed to fetch fragments worker");

    const workerBlob = await fetched.blob();
    const workerFile = new File([workerBlob], "worker.mjs", {
      type: "text/javascript",
    });
    const workerUrl = URL.createObjectURL(workerFile);

    this.fragments.init(workerUrl);

    // 2️⃣ AFTER init → attach listeners
    this.world.camera.controls.addEventListener("update", () => {
      this.fragments.core.update();
    });

    this.fragments.list.onItemSet.add(({ value: model }) => {
      model.useCamera(this.world.camera.three);
      this.world.scene.three.add(model.object);
      this.fragments.core.update(true);
    });

    await this.ifcLoader.setup({
    autoSetWasm: false,
    wasm: {
        path: "/wasm/", // Set to public path where the IFC WASM files are hosted
        absolute: false,
    },
    });
  }

  async loadIFCFromArrayBuffer(arrayBuffer: ArrayBuffer, name = "model.ifc") {
    const buffer = new Uint8Array(arrayBuffer);
    await this.ifcLoader.load(buffer, false, name);
  }

  dispose() {
    this.components.dispose();
  }
}
