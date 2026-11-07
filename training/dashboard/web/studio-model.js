import * as THREE from 'three';
import { OrbitControls } from './vendor/three/addons/OrbitControls.js';
import { RoomEnvironment } from './vendor/three/addons/RoomEnvironment.js';

let sharedModel;
let sharedUsers = 0;

function loadModel() {
  if (!sharedModel) sharedModel = new Promise((resolve, reject) => {
    const worker = new Worker('/studio-model/model-worker.js');
    const timeout = setTimeout(() => { worker.terminate(); reject(new Error('Studio 模型解码超时')); }, 60000);
    worker.onerror = event => { clearTimeout(timeout); worker.terminate(); reject(new Error(event.message || 'Studio 模型加载失败')); };
    worker.onmessage = event => {
      clearTimeout(timeout);
      worker.terminate();
      if (!event.data.ok) return reject(new Error(event.data.error));
      const geometries = {};
      for (const [name, mesh] of Object.entries(event.data.meshes)) {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(mesh.position, 3));
        geometry.setAttribute('normal', new THREE.BufferAttribute(mesh.normal, 3));
        if (mesh.index) geometry.setIndex(new THREE.BufferAttribute(mesh.index, 1));
        geometries[name] = geometry;
      }
      resolve({ model: event.data.mj, geometries });
    };
    worker.postMessage({ base: new URL('/studio-model/model/', location.href).href });
  }).catch(error => { sharedModel = null; throw error; });
  return sharedModel;
}

function materialFor(rgba) {
  const [red, green, blue] = rgba;
  const near = (r, g, b) => Math.abs(red - r) < .04 && Math.abs(green - g) < .04 && Math.abs(blue - b) < .04;
  let color = new THREE.Color(red, green, blue), roughness = .5;
  if (near(.98, .71, 0)) { color = new THREE.Color('#F5B400'); roughness = .42; }
  else if (near(.29, .29, .29)) { color = new THREE.Color('#5E6167'); roughness = .58; }
  else if (near(.35, .38, .40)) { color = new THREE.Color('#4C5157'); roughness = .55; }
  else if (near(.26, .28, .30)) { color = new THREE.Color('#2F3338'); roughness = .4; }
  else if (near(.54, .85, .83)) { color = new THREE.Color('#86D3CC'); roughness = .6; }
  else if (red > .75 && green > .75 && blue > .75) color = new THREE.Color('#ECECE8');
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0, envMapIntensity: .55 });
}

const quaternion = values => new THREE.Quaternion(values[1], values[2], values[3], values[0]).normalize();

export class StudioReplay {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, 1, .005, 100);
    this.camera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.minDistance = .15;
    this.controls.maxDistance = 15;
    this.controls.addEventListener('change', () => { this.dirty = true; });
    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.joints = {};
    this.materials = [];
    this.follow = true;
    this.dirty = true;
    this.target = new THREE.Vector3(0, 0, .14);
    const room = new RoomEnvironment();
    const generator = new THREE.PMREMGenerator(this.renderer);
    this.environment = generator.fromScene(room, .04);
    this.scene.environment = this.environment.texture;
    generator.dispose(); room.dispose();
    const key = new THREE.DirectionalLight(0xfff0dc, 2.4); key.position.set(.35, .3, 1.4);
    const fill = new THREE.DirectionalLight(0xe4ecff, .8); fill.position.set(.3, -.8, .35);
    const rim = new THREE.DirectionalLight(0xcfe0ff, 1.8); rim.position.set(-.7, -.5, .6);
    this.scene.add(key, fill, rim, new THREE.HemisphereLight(0xffffff, 0x2a2b2f, .35));
    this.grid = new THREE.GridHelper(20, 200, 0x235267, 0x152c3f);
    this.grid.rotation.x = Math.PI / 2;
    this.scene.add(this.grid);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(canvas);
    this.setView('perspective');
    this.loop = () => {
      if (this.disposed) return;
      this.controls.update();
      if (this.dirty) { this.renderer.render(this.scene, this.camera); this.dirty = false; }
      this.animation = requestAnimationFrame(this.loop);
    };
    this.loop();
  }

  async load() {
    const { model, geometries } = await loadModel();
    if (this.disposed) return;
    sharedUsers += 1;
    this.loaded = true;
    const bodies = [];
    for (const body of model.bodies) {
      const node = new THREE.Group();
      if (body.parent >= 0) { node.position.fromArray(body.pos); node.quaternion.copy(quaternion(body.quat)); }
      let attachment = node;
      if (body.joint) {
        attachment = new THREE.Group(); node.add(attachment);
        this.joints[body.joint.name] = { pivot: attachment, axis: new THREE.Vector3(...body.joint.axis).normalize() };
      }
      for (const geom of body.geoms) {
        if (!geometries[geom.mesh]) throw new Error(`Studio 缺少网格：${geom.mesh}`);
        const material = materialFor(geom.rgba); this.materials.push(material);
        const mesh = new THREE.Mesh(geometries[geom.mesh], material);
        mesh.position.fromArray(geom.pos); mesh.quaternion.copy(quaternion(geom.quat)); attachment.add(mesh);
      }
      bodies.push(attachment);
      if (body.parent < 0) this.root.add(node); else bodies[body.parent].add(node);
    }
    this.root.visible = false;
    this.dirty = true;
  }

  setFrame(frame) {
    if (!this.loaded) return;
    const position = frame.root_position_m;
    const rotation = frame.root_quaternion_wxyz;
    if (!Array.isArray(position) || !Array.isArray(rotation) || position.length !== 3 || rotation.length !== 4 || ![...position, ...rotation].every(Number.isFinite)) return;
    this.root.visible = true;
    this.root.position.fromArray(position);
    this.root.quaternion.copy(quaternion(rotation));
    for (const [name, joint] of Object.entries(this.joints)) {
      const angle = name === 'mouth' ? 0 : frame.joints_rad?.[name];
      if (Number.isFinite(angle)) joint.pivot.quaternion.setFromAxisAngle(joint.axis, angle);
    }
    if (this.follow) {
      const target = new THREE.Vector3(...position).add(new THREE.Vector3(0, 0, .025));
      this.camera.position.add(target.clone().sub(this.controls.target));
      this.controls.target.copy(target);
      this.target.copy(target);
    }
    this.dirty = true;
  }

  setView(view) {
    const offsets = { perspective: [.55, -.6, .38], front: [.7, 0, .13], side: [0, -.7, .13], top: [.001, 0, .85] };
    this.camera.position.copy(this.target).add(new THREE.Vector3(...(offsets[view] || offsets.perspective)));
    this.controls.target.copy(this.target); this.controls.update(); this.dirty = true;
  }

  resize() {
    const width = this.canvas.clientWidth, height = this.canvas.clientHeight;
    if (!width || !height) return;
    this.renderer.setSize(width, height, false); this.camera.aspect = width / height; this.camera.updateProjectionMatrix(); this.dirty = true;
  }

  dispose() {
    this.disposed = true; cancelAnimationFrame(this.animation); this.observer.disconnect(); this.controls.dispose();
    this.materials.forEach(material => material.dispose());
    this.grid.geometry.dispose(); this.grid.material.dispose(); this.environment.dispose();
    this.renderer.dispose(); this.renderer.forceContextLoss();
    if (this.loaded && --sharedUsers === 0) {
      const oldModel = sharedModel; sharedModel = null;
      oldModel?.then(({ geometries }) => Object.values(geometries).forEach(geometry => geometry.dispose()));
    }
  }
}
