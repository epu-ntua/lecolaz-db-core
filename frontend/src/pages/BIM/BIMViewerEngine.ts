/**
 * BIMViewerEngine
 * ----------------
 * This class encapsulates the entire 3D rendering pipeline for IFC models.
 *
 * Responsibilities:
 * - Creates and configures the ThatOpen Components system
 * - Sets up the Three.js scene, camera, and renderer
 * - Initializes the FragmentsManager (geometry handling via worker)
 * - Configures the IFC loader (WebIFC + WASM)
 * - Loads IFC models from an ArrayBuffer into the scene
 * - Manages proper cleanup of WebGL and worker resources
 *
 * Important:
 * - This class is framework-agnostic (no React, no routing, no API logic).
 * - It only handles rendering and IFC processing.
 * - The React layer is responsible for lifecycle and data fetching.
 */

import * as OBC from '@thatopen/components';
import * as FRAGS from '@thatopen/fragments';
import * as THREE from 'three';

const HIGHLIGHT_STYLE: FRAGS.MaterialDefinition = {
  color: new THREE.Color('#ff4d00'),
  renderedFaces: FRAGS.RenderedFaces.TWO,
  opacity: 0.85,
  transparent: true,
  preserveOriginalMaterial: true,
  depthTest: false,
  depthWrite: false,
};

export class BIMViewerEngine {
  private components: OBC.Components;
  private world: OBC.World;

  // Keep concrete types so TS knows methods exist
  private scene: OBC.SimpleScene;
  private camera: OBC.SimpleCamera;
  private renderer: OBC.SimpleRenderer;

  private fragments?: OBC.FragmentsManager;
  private ifcLoader?: OBC.IfcLoader;

  private workerUrl?: string;

  constructor(container: HTMLElement) {
    this.components = new OBC.Components();

    const worlds = this.components.get(OBC.Worlds);
    const world = worlds.create<OBC.SimpleScene, OBC.SimpleCamera, OBC.SimpleRenderer>();
    if (!world) throw new Error('Failed to create world');
    this.world = world;

    // Create concrete instances and keep references
    this.scene = new OBC.SimpleScene(this.components);
    this.renderer = new OBC.SimpleRenderer(this.components, container);
    this.camera = new OBC.SimpleCamera(this.components);

    // Attach to world
    this.world.scene = this.scene;
    this.world.renderer = this.renderer;
    this.world.camera = this.camera;

    // Minimal init in constructor (no IFC/worker/wasm here)
    this.components.init();
    this.scene.setup();
  }

  // Call this once after construction
  async initIfcPipeline() {
    this.fragments = this.components.get(OBC.FragmentsManager);
    this.ifcLoader = this.components.get(OBC.IfcLoader);
    console.log('[BIMViewerEngine] initIfcPipeline start');

    // Ensure camera controls exist
    const controls = this.camera.controls;
    if (!controls) throw new Error('Camera controls not available');

    // Worker (consider moving local later; this keeps your current behavior)
    const workerSrc = 'https://thatopen.github.io/engine_fragment/resources/worker.mjs';
    const fetched = await fetch(workerSrc);
    if (!fetched.ok) throw new Error('Failed to fetch fragments worker');

    const workerBlob = await fetched.blob();
    const workerFile = new File([workerBlob], 'worker.mjs', { type: 'text/javascript' });
    this.workerUrl = URL.createObjectURL(workerFile);

    this.fragments.init(this.workerUrl);
    console.log('[BIMViewerEngine] fragments worker initialized');

    // Fragments update hooks
    controls.addEventListener('update', () => {
      this.fragments?.core.update();
    });

    this.fragments.list.onItemSet.add(({ value: model }) => {
      model.useCamera(this.camera.three);
      this.scene.three.add(model.object);
      this.fragments?.core.update(true);
    });

    // WASM path must be manual
    await this.ifcLoader.setup({
      autoSetWasm: false,
      wasm: { path: '/wasm/', absolute: false },
    });
    console.log('[BIMViewerEngine] ifc loader setup complete');
  }

  async loadIFCFromArrayBuffer(arrayBuffer: ArrayBuffer, name = 'model.ifc') {
    if (!this.ifcLoader) {
      throw new Error('IFC loader not initialized. Call initIfcPipeline() first.');
    }
    const buffer = new Uint8Array(arrayBuffer);
    await this.ifcLoader.load(buffer, false, name);
    console.log('[BIMViewerEngine] loadIFCFromArrayBuffer complete', {
      name,
      bytes: arrayBuffer.byteLength,
    });
  }

  async highlightByGlobalIds(globalIds: string[]) {
    console.log('[BIMViewerEngine] highlight request', { globalIds });
    if (!this.fragments) {
      console.warn('[BIMViewerEngine] highlight skipped: fragments not initialized');
      return;
    }

    await this.fragments.resetHighlight();
    this.fragments.core.update(true);

    if (globalIds.length === 0) {
      return;
    }

    const modelIdMap = await this.fragments.guidsToModelIdMap(globalIds);
    const rawModelIdMap = OBC.ModelIdMapUtils.toRaw(modelIdMap);
    console.log('[BIMViewerEngine] guid lookup result', globalIds, rawModelIdMap);
    if (OBC.ModelIdMapUtils.isEmpty(modelIdMap)) {
      console.warn('No IFC items found for global ids', globalIds);
      return;
    }

    try {
      const [itemData, boxes, positions] = await Promise.all([
        this.fragments.getData(modelIdMap),
        this.fragments.getBBoxes(modelIdMap),
        this.fragments.getPositions(modelIdMap),
      ]);
      console.log(
        '[BIMViewerEngine] matched item diagnostics',
        globalIds,
        'boxes=',
        boxes.length,
        'positions=',
        positions.length,
        'itemData=',
        itemData,
      );
    } catch (error) {
      console.error('[BIMViewerEngine] diagnostics failed', error);
    }

    await this.fragments.highlight(HIGHLIGHT_STYLE, modelIdMap);
    this.fragments.core.update(true);
    await this.camera.fitToItems(modelIdMap);
    await this.camera.setOrbitToItems(modelIdMap);
    console.log('[BIMViewerEngine] highlight applied', globalIds, rawModelIdMap);
  }

  dispose() {
    // Revoke worker blob URL if we created it
    if (this.workerUrl) URL.revokeObjectURL(this.workerUrl);

    this.components.dispose();
  }
}
