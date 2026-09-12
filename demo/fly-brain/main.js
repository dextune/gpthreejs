(() => {
  'use strict';

  if (!window.THREE) {
    const panel = document.getElementById('startPanel');
    if (panel) panel.innerHTML = '<h2>THREE.JS NOT FOUND</h2><p>Connect to the internet once or use the packaged ZIP.</p>';
    return;
  }

  const CONFIG = Object.freeze({
    worldHalfHeight: 5,
    cameraHeight: 10,
    gravity: -19.5,
    flapForce: 7.35,
    maxFallSpeed: -9.8,
    scrollSpeed: 4.15,
    maxScrollBonus: 2.15,
    obstacleGap: 3.25,
    minObstacleGap: 2.58,
    spawnDistance: 7.1,
    obstacleWidth: 1.12,
    obstaclePoolSize: 8,
    flyCollisionRadius: 0.49,
    pixelRatioLimit: 1.7,
    maxDelta: 0.045,
    physicsStepMax: 1 / 60,
    gameOverPanelDelay: 0.42,
    particlePoolSize: 34,
    scienceHudIntervalMin: 4.5,
    scienceHudIntervalMax: 7.5
  });

  const STATE = Object.freeze({ READY: 0, RUNNING: 1, GAMEOVER: 2 });
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const rand = (a, b) => a + Math.random() * (b - a);

  class RendererSystem {
    constructor(host) {
      this.host = host;
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0xdff1ea, 15, 31);

      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
      });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, CONFIG.pixelRatioLimit));
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.02;
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.setClearColor(0x000000, 0);
      this.host.appendChild(this.renderer.domElement);

      this.camera = new THREE.OrthographicCamera(-8, 8, 5, -5, 0.1, 50);
      this.camera.position.set(0, 0.15, 14);
      this.camera.lookAt(0, 0, 0);

      const hemi = new THREE.HemisphereLight(0xffffff, 0x66807c, 2.0);
      this.scene.add(hemi);

      this.sun = new THREE.DirectionalLight(0xfff6dc, 2.5);
      this.sun.position.set(-5, 9, 11);
      this.sun.castShadow = true;
      this.sun.shadow.mapSize.set(768, 768);
      this.sun.shadow.camera.left = -10;
      this.sun.shadow.camera.right = 10;
      this.sun.shadow.camera.top = 8;
      this.sun.shadow.camera.bottom = -8;
      this.sun.shadow.camera.near = 1;
      this.sun.shadow.camera.far = 32;
      this.sun.shadow.bias = -0.0006;
      this.scene.add(this.sun);

      this.aspect = 1;
      this.viewWidth = 16;
      this.resize();
    }

    resize() {
      const w = Math.max(1, window.innerWidth);
      const h = Math.max(1, window.innerHeight);
      this.aspect = w / h;

      const verticalBoost = this.aspect < 0.75 ? 1.13 : 1;
      const height = CONFIG.cameraHeight * verticalBoost;
      this.viewWidth = height * this.aspect;
      this.camera.left = -this.viewWidth / 2;
      this.camera.right = this.viewWidth / 2;
      this.camera.top = height / 2;
      this.camera.bottom = -height / 2;
      this.camera.updateProjectionMatrix();

      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, CONFIG.pixelRatioLimit));
      this.renderer.setSize(w, h, false);
    }

    render() {
      this.renderer.render(this.scene, this.camera);
    }
  }

  class AudioManager {
    constructor() {
      this.ctx = null;
      this.master = null;
      this.muted = false;
    }

    ensure() {
      if (!this.ctx) {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        this.ctx = new Ctx();
        this.master = this.ctx.createGain();
        this.master.gain.value = this.muted ? 0 : 0.72;
        this.master.connect(this.ctx.destination);
      }
      if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
    }

    setMuted(value) {
      this.muted = value;
      if (this.master && this.ctx) {
        this.master.gain.cancelScheduledValues(this.ctx.currentTime);
        this.master.gain.setTargetAtTime(value ? 0 : 0.72, this.ctx.currentTime, 0.015);
      }
    }

    tone(type, startHz, endHz, duration, volume) {
      if (!this.ctx || !this.master || this.muted) return;
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(startHz, now);
      osc.frequency.exponentialRampToValueAtTime(Math.max(40, endHz), now + duration);
      gain.gain.setValueAtTime(volume, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      osc.connect(gain);
      gain.connect(this.master);
      osc.start(now);
      osc.stop(now + duration + 0.015);
    }

    flap() {
      this.tone('triangle', 460, 215, 0.075, 0.045);
    }

    score() {
      this.tone('sine', 760, 1120, 0.085, 0.04);
    }

    bonk() {
      this.tone('sine', 160, 72, 0.19, 0.075);
    }
  }

  class UIManager {
    constructor(audio) {
      this.audio = audio;
      this.scoreEl = document.getElementById('score');
      this.bestEl = document.getElementById('bestScore');
      this.startPanel = document.getElementById('startPanel');
      this.gameOverPanel = document.getElementById('gameOverPanel');
      this.finalScore = document.getElementById('finalScore');
      this.finalBest = document.getElementById('finalBest');
      this.retryButton = document.getElementById('retry');
      this.soundButton = document.getElementById('soundToggle');
      this.scienceHud = document.getElementById('scienceHud');
      this.scienceTitle = document.getElementById('scienceTitle');
      this.scienceText = document.getElementById('scienceText');
      this.lastScore = -1;
      this.hudTimer = 2.4;
      this.hudVisibleTimer = 0;
      this.hudIndex = 0;
      this.messages = [
        ['SYNAPSES ONLINE', 'MOTOR PLAN: MOSTLY VIBES'],
        ['NEURAL ACTIVITY', '166,700 NEURONS ARGUING'],
        ['FLY IQ', 'QUESTIONABLE · CONFIDENCE HIGH'],
        ['CONNECTOME STATUS', 'STILL SOMEHOW FLYING'],
        ['RESEARCH NOTE', 'ETHICS COMMITTEE TYPING…'],
        ['SENSOR FUSION', 'CUP DETECTED · PANIC OPTIONAL']
      ];
      this.setScore(0);
    }

    setBest(value) {
      this.bestEl.textContent = String(value);
    }

    setScore(value) {
      if (value === this.lastScore) return;
      this.lastScore = value;
      this.scoreEl.textContent = String(value);
    }

    showReady() {
      this.startPanel.classList.remove('is-hidden');
      this.gameOverPanel.classList.add('is-hidden');
      this.scienceHud.classList.remove('is-visible');
    }

    showRunning() {
      this.startPanel.classList.add('is-hidden');
      this.gameOverPanel.classList.add('is-hidden');
    }

    showGameOver(score, best) {
      this.finalScore.textContent = String(score);
      this.finalBest.textContent = String(best);
      this.gameOverPanel.classList.remove('is-hidden');
      this.scienceHud.classList.remove('is-visible');
      this.scienceTitle.textContent = 'NEURAL ACTIVITY';
      this.scienceText.textContent = '0% · BRAIN CURRENTLY OFFLINE';
    }

    update(dt, running) {
      if (!running) return;
      if (this.hudVisibleTimer > 0) {
        this.hudVisibleTimer -= dt;
        if (this.hudVisibleTimer <= 0) this.scienceHud.classList.remove('is-visible');
        return;
      }
      this.hudTimer -= dt;
      if (this.hudTimer <= 0) {
        const message = this.messages[this.hudIndex % this.messages.length];
        this.hudIndex += 1;
        this.scienceTitle.textContent = message[0];
        this.scienceText.textContent = message[1];
        this.scienceHud.classList.add('is-visible');
        this.hudVisibleTimer = 2.15;
        this.hudTimer = rand(CONFIG.scienceHudIntervalMin, CONFIG.scienceHudIntervalMax);
      }
    }
  }

  class ParticleManager {
    constructor(scene) {
      this.scene = scene;
      this.pool = [];
      this.cursor = 0;
      this.geo = new THREE.SphereGeometry(0.085, 7, 5);
      this.mat = new THREE.MeshBasicMaterial({
        color: 0xe7ffff,
        transparent: true,
        opacity: 0.78,
        depthWrite: false
      });

      for (let i = 0; i < CONFIG.particlePoolSize; i += 1) {
        const mesh = new THREE.Mesh(this.geo, this.mat.clone());
        mesh.visible = false;
        mesh.renderOrder = 5;
        scene.add(mesh);
        this.pool.push({ mesh, vx: 0, vy: 0, life: 0, maxLife: 1, spin: 0 });
      }
    }

    emitOne(x, y, z, vx, vy, life, scale) {
      const p = this.pool[this.cursor];
      this.cursor = (this.cursor + 1) % this.pool.length;
      p.mesh.visible = true;
      p.mesh.position.set(x, y, z);
      p.mesh.scale.setScalar(scale);
      p.mesh.material.opacity = 0.72;
      p.vx = vx;
      p.vy = vy;
      p.life = life;
      p.maxLife = life;
      p.spin = rand(-4, 4);
    }

    emitFlap(x, y) {
      this.emitOne(x - 0.55, y + 0.08, 0.25, -1.55, 0.45, 0.42, 0.7);
      this.emitOne(x - 0.72, y - 0.12, 0.18, -1.15, -0.15, 0.36, 0.5);
    }

    emitScore(x, y) {
      this.emitOne(x + 0.55, y + 0.45, 0.4, -0.35, 1.05, 0.5, 0.52);
      this.emitOne(x + 0.72, y + 0.12, 0.35, -0.1, 0.8, 0.42, 0.4);
    }

    update(dt) {
      for (let i = 0; i < this.pool.length; i += 1) {
        const p = this.pool[i];
        if (!p.mesh.visible) continue;
        p.life -= dt;
        if (p.life <= 0) {
          p.mesh.visible = false;
          continue;
        }
        p.mesh.position.x += p.vx * dt;
        p.mesh.position.y += p.vy * dt;
        p.vy -= 1.35 * dt;
        p.mesh.rotation.z += p.spin * dt;
        const t = p.life / p.maxLife;
        p.mesh.material.opacity = 0.72 * t;
        const s = 0.65 + (1 - t) * 0.75;
        p.mesh.scale.multiplyScalar(1 + dt * 0.75);
        if (p.mesh.scale.x > s + 0.9) p.mesh.scale.setScalar(s);
      }
    }
  }

  class Fly {
    constructor(scene, particles, audio) {
      this.scene = scene;
      this.particles = particles;
      this.audio = audio;
      this.root = new THREE.Group();
      this.visual = new THREE.Group();
      this.squash = new THREE.Group();
      this.root.add(this.visual);
      this.visual.add(this.squash);
      this.scene.add(this.root);

      this.velocityY = 0;
      this.flapPulse = 0;
      this.dead = false;
      this.spinVelocity = 0;
      this.time = 0;
      this.lookTimer = 0.5;
      this.lookX = 0;
      this.lookY = 0;

      this.makeModel();
      this.reset(0);
    }

    makeModel() {
      const navy = new THREE.MeshStandardMaterial({ color: 0x454b64, roughness: 0.66, metalness: 0.02 });
      const navyLight = new THREE.MeshStandardMaterial({ color: 0x5a607a, roughness: 0.7, metalness: 0.01 });
      const cream = new THREE.MeshStandardMaterial({ color: 0xfffae8, roughness: 0.55, metalness: 0 });
      const pupil = new THREE.MeshToonMaterial({ color: 0x24333d });
      const mouthMat = new THREE.MeshToonMaterial({ color: 0x8a5c68 });
      const legMat = new THREE.MeshToonMaterial({ color: 0x3c4555 });
      const wingMat = new THREE.MeshStandardMaterial({
        color: 0xcffbff,
        roughness: 0.34,
        metalness: 0,
        transparent: true,
        opacity: 0.56,
        depthWrite: false,
        side: THREE.DoubleSide
      });

      const sphereHi = new THREE.SphereGeometry(1, 24, 18);
      const sphereMed = new THREE.SphereGeometry(1, 18, 14);
      const eyeGeo = new THREE.SphereGeometry(1, 18, 14);

      this.body = new THREE.Mesh(sphereHi, navy);
      this.body.position.set(-0.42, -0.02, 0);
      this.body.scale.set(0.72, 0.58, 0.62);
      this.body.castShadow = true;
      this.squash.add(this.body);

      const belly = new THREE.Mesh(sphereMed, navyLight);
      belly.position.set(-0.62, -0.1, 0.17);
      belly.scale.set(0.49, 0.38, 0.46);
      this.squash.add(belly);

      this.head = new THREE.Mesh(sphereHi, navy);
      this.head.position.set(0.28, 0.13, 0.05);
      this.head.scale.set(0.73, 0.7, 0.66);
      this.head.castShadow = true;
      this.squash.add(this.head);

      this.eyeLeft = new THREE.Mesh(eyeGeo, cream);
      this.eyeLeft.position.set(0.44, 0.33, 0.57);
      this.eyeLeft.scale.set(0.29, 0.34, 0.15);
      this.squash.add(this.eyeLeft);

      this.eyeRight = new THREE.Mesh(eyeGeo, cream);
      this.eyeRight.position.set(0.74, 0.19, 0.48);
      this.eyeRight.scale.set(0.285, 0.33, 0.145);
      this.squash.add(this.eyeRight);

      this.pupilLeft = new THREE.Mesh(eyeGeo, pupil);
      this.pupilLeft.position.set(0.47, 0.33, 0.708);
      this.pupilLeft.scale.set(0.105, 0.135, 0.045);
      this.squash.add(this.pupilLeft);

      this.pupilRight = new THREE.Mesh(eyeGeo, pupil);
      this.pupilRight.position.set(0.78, 0.19, 0.622);
      this.pupilRight.scale.set(0.105, 0.135, 0.045);
      this.squash.add(this.pupilRight);

      this.mouth = new THREE.Mesh(sphereMed, mouthMat);
      this.mouth.position.set(0.72, -0.14, 0.60);
      this.mouth.scale.set(0.075, 0.035, 0.025);
      this.squash.add(this.mouth);

      const wingGeo = new THREE.CircleGeometry(0.62, 24);
      this.wingLeft = new THREE.Mesh(wingGeo, wingMat);
      this.wingLeft.position.set(-0.59, 0.37, -0.08);
      this.wingLeft.scale.set(1.18, 0.52, 1);
      this.wingLeft.rotation.z = 0.44;
      this.squash.add(this.wingLeft);

      this.wingRight = new THREE.Mesh(wingGeo, wingMat.clone());
      this.wingRight.material.opacity = 0.45;
      this.wingRight.position.set(-0.65, -0.25, -0.04);
      this.wingRight.scale.set(1.08, 0.47, 1);
      this.wingRight.rotation.z = -0.36;
      this.squash.add(this.wingRight);

      const legGeo = new THREE.CylinderGeometry(0.028, 0.038, 0.52, 6);
      this.legs = new THREE.Group();
      const legSpecs = [
        [-0.65, -0.43, 0.19, 0.48],
        [-0.22, -0.49, 0.18, -0.10],
        [0.06, -0.42, 0.17, -0.55]
      ];
      for (let i = 0; i < legSpecs.length; i += 1) {
        const spec = legSpecs[i];
        const leg = new THREE.Mesh(legGeo, legMat);
        leg.position.set(spec[0], spec[1], spec[2]);
        leg.rotation.z = spec[3];
        this.legs.add(leg);
      }
      this.squash.add(this.legs);

      const shineMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.26, depthWrite: false });
      const shine = new THREE.Mesh(sphereMed, shineMat);
      shine.position.set(0.04, 0.44, 0.52);
      shine.scale.set(0.18, 0.08, 0.03);
      this.squash.add(shine);
    }

    setX(x) {
      this.root.position.x = x;
    }

    reset(y) {
      this.root.position.y = y;
      this.root.position.z = 0.8;
      this.visual.rotation.z = 0;
      this.visual.rotation.y = 0;
      this.squash.scale.set(1, 1, 1);
      this.velocityY = 0;
      this.flapPulse = 0;
      this.dead = false;
      this.spinVelocity = 0;
      this.time = 0;
      this.lookTimer = 0.8;
    }

    flap() {
      if (this.dead) return;
      this.velocityY = CONFIG.flapForce;
      this.flapPulse = 1;
      this.particles.emitFlap(this.root.position.x, this.root.position.y);
      this.audio.flap();
    }

    crash() {
      if (this.dead) return;
      this.dead = true;
      this.velocityY = 3.0;
      this.spinVelocity = -5.4;
      this.flapPulse = 1.35;
      this.squash.scale.set(1.28, 0.68, 1.05);
      this.audio.bonk();
    }

    updateEyes(dt) {
      this.lookTimer -= dt;
      if (this.lookTimer <= 0) {
        this.lookTimer = rand(1.7, 4.0);
        this.lookX = rand(-0.035, 0.065);
        this.lookY = rand(-0.045, 0.05);
      }
      const follow = 1 - Math.exp(-dt * 7);
      const baseLX = 0.47;
      const baseLY = 0.33;
      const baseRX = 0.78;
      const baseRY = 0.19;
      this.pupilLeft.position.x = lerp(this.pupilLeft.position.x, baseLX + this.lookX, follow);
      this.pupilLeft.position.y = lerp(this.pupilLeft.position.y, baseLY + this.lookY, follow);
      this.pupilRight.position.x = lerp(this.pupilRight.position.x, baseRX + this.lookX, follow);
      this.pupilRight.position.y = lerp(this.pupilRight.position.y, baseRY + this.lookY, follow);
    }

    animateVisual(dt, ready) {
      this.time += dt;
      const wingBoost = this.flapPulse > 0.03 ? 1.35 : 1;
      const wingPhase = this.time * 46 * wingBoost;
      this.wingLeft.rotation.z = 0.44 + Math.sin(wingPhase) * 0.31;
      this.wingRight.rotation.z = -0.36 - Math.sin(wingPhase + 0.6) * 0.28;
      this.wingLeft.scale.y = 0.50 + Math.abs(Math.sin(wingPhase)) * 0.09;
      this.wingRight.scale.y = 0.45 + Math.abs(Math.sin(wingPhase + 0.6)) * 0.08;

      this.updateEyes(dt);

      if (ready) {
        const bob = Math.sin(this.time * 2.2) * 0.07;
        this.root.position.y = bob;
        this.visual.rotation.z = Math.sin(this.time * 1.55) * 0.028;
      }

      if (this.flapPulse > 0) {
        this.flapPulse = Math.max(0, this.flapPulse - dt * 5.8);
      }
      const p = clamp(this.flapPulse, 0, 1);
      const sx = 1 - p * 0.09;
      const sy = 1 + p * 0.16;
      const follow = 1 - Math.exp(-dt * 14);
      this.squash.scale.x = lerp(this.squash.scale.x, sx, follow);
      this.squash.scale.y = lerp(this.squash.scale.y, sy, follow);
      this.squash.scale.z = lerp(this.squash.scale.z, 1, follow);
    }

    physics(dt) {
      if (this.dead) {
        this.velocityY = Math.max(CONFIG.maxFallSpeed * 1.25, this.velocityY + CONFIG.gravity * 0.82 * dt);
        this.root.position.y += this.velocityY * dt;
        this.visual.rotation.z += this.spinVelocity * dt;
        this.squash.scale.x = lerp(this.squash.scale.x, 0.95, 1 - Math.exp(-dt * 4));
        this.squash.scale.y = lerp(this.squash.scale.y, 1.05, 1 - Math.exp(-dt * 4));
        return;
      }

      this.velocityY = Math.max(CONFIG.maxFallSpeed, this.velocityY + CONFIG.gravity * dt);
      this.root.position.y += this.velocityY * dt;
      const targetRotation = clamp(this.velocityY * 0.045, -0.48, 0.32);
      this.visual.rotation.z = lerp(this.visual.rotation.z, targetRotation, 1 - Math.exp(-dt * 8.5));
    }
  }

  class World {
    constructor(scene) {
      this.scene = scene;
      this.far = new THREE.Group();
      this.mid = new THREE.Group();
      this.near = new THREE.Group();
      this.scene.add(this.far, this.mid, this.near);

      this.farSpan = 40;
      this.midSpan = 42;
      this.nearSpan = 38;
      this.createFar();
      this.createMid();
      this.createNear();
      this.createBoundsDecor();
    }

    createFar() {
      const cloudMat = new THREE.MeshBasicMaterial({ color: 0xf7fffb, transparent: true, opacity: 0.34, depthWrite: false });
      const nodeMat = new THREE.MeshBasicMaterial({ color: 0xc0ded8, transparent: true, opacity: 0.26, depthWrite: false });
      const cloudGeo = new THREE.SphereGeometry(1, 12, 8);
      const nodeGeo = new THREE.SphereGeometry(0.16, 8, 6);
      const lineGeo = new THREE.CylinderGeometry(0.025, 0.025, 1, 5);

      for (let i = 0; i < 10; i += 1) {
        const g = new THREE.Group();
        g.position.set(-18 + i * 4.2, rand(-2.7, 3.4), -8.0);
        const cloud = new THREE.Mesh(cloudGeo, cloudMat);
        cloud.scale.set(rand(1.3, 2.3), rand(0.45, 0.85), 0.3);
        g.add(cloud);
        if (i % 2 === 0) {
          const n1 = new THREE.Mesh(nodeGeo, nodeMat);
          const n2 = new THREE.Mesh(nodeGeo, nodeMat);
          const link = new THREE.Mesh(lineGeo, nodeMat);
          n1.position.set(-0.7, -0.6, 0.2);
          n2.position.set(0.7, 0.3, 0.2);
          link.scale.y = 1.62;
          link.rotation.z = -0.98;
          link.position.set(0, -0.15, 0.2);
          g.add(n1, n2, link);
        }
        this.far.add(g);
      }
    }

    createMid() {
      const shelfMat = new THREE.MeshToonMaterial({ color: 0xa9c9c2 });
      const glassMat = new THREE.MeshStandardMaterial({ color: 0xcdf3ee, roughness: 0.25, transparent: true, opacity: 0.38, depthWrite: false });
      const darkMat = new THREE.MeshToonMaterial({ color: 0x78928e });
      const boxGeo = new THREE.BoxGeometry(1, 1, 1);
      const cylGeo = new THREE.CylinderGeometry(0.34, 0.42, 1, 12);
      const sphereGeo = new THREE.SphereGeometry(0.5, 12, 8);

      for (let i = 0; i < 8; i += 1) {
        const g = new THREE.Group();
        g.position.set(-17 + i * 5.4, -2.9 + (i % 3) * 0.2, -5.1);

        const shelf = new THREE.Mesh(boxGeo, shelfMat);
        shelf.scale.set(3.2, 0.11, 0.38);
        shelf.position.y = -0.55;
        g.add(shelf);

        if (i % 3 === 0) {
          const cup = new THREE.Mesh(cylGeo, glassMat);
          cup.scale.set(0.9, 1.45, 0.65);
          cup.position.set(-0.55, 0.15, 0);
          const orb = new THREE.Mesh(sphereGeo, glassMat);
          orb.scale.set(0.7, 0.45, 0.4);
          orb.position.set(0.55, -0.12, 0.02);
          g.add(cup, orb);
        } else if (i % 3 === 1) {
          for (let k = 0; k < 4; k += 1) {
            const book = new THREE.Mesh(boxGeo, k % 2 ? shelfMat : darkMat);
            book.scale.set(0.9 + k * 0.08, 0.19, 0.48);
            book.position.set(0.1, -0.38 + k * 0.2, 0);
            g.add(book);
          }
        } else {
          const monitor = new THREE.Mesh(boxGeo, darkMat);
          monitor.scale.set(1.35, 0.82, 0.18);
          monitor.position.y = 0.15;
          const stand = new THREE.Mesh(boxGeo, shelfMat);
          stand.scale.set(0.18, 0.6, 0.17);
          stand.position.y = -0.5;
          g.add(monitor, stand);
        }
        this.mid.add(g);
      }
    }

    createNear() {
      const mat = new THREE.MeshToonMaterial({ color: 0xb2d5cc, transparent: true, opacity: 0.72 });
      const potMat = new THREE.MeshToonMaterial({ color: 0xd6a898, transparent: true, opacity: 0.7 });
      const stemGeo = new THREE.CylinderGeometry(0.08, 0.11, 2.1, 7);
      const leafGeo = new THREE.SphereGeometry(0.5, 10, 7);
      const potGeo = new THREE.CylinderGeometry(0.45, 0.32, 0.65, 10);

      for (let i = 0; i < 7; i += 1) {
        const g = new THREE.Group();
        g.position.set(-16 + i * 5.8, -4.0, -2.7);
        if (i % 2 === 0) {
          const pot = new THREE.Mesh(potGeo, potMat);
          pot.position.y = -0.36;
          g.add(pot);
          const stem = new THREE.Mesh(stemGeo, mat);
          stem.position.y = 0.85;
          stem.rotation.z = i % 4 === 0 ? 0.1 : -0.1;
          g.add(stem);
          const leaf1 = new THREE.Mesh(leafGeo, mat);
          leaf1.scale.set(0.68, 0.26, 0.24);
          leaf1.position.set(0.4, 1.35, 0.1);
          leaf1.rotation.z = 0.45;
          g.add(leaf1);
        }
        this.near.add(g);
      }
    }

    createBoundsDecor() {
      const deskMat = new THREE.MeshStandardMaterial({ color: 0xc2ddd4, roughness: 0.9, metalness: 0 });
      this.desk = new THREE.Mesh(new THREE.BoxGeometry(30, 1.1, 5), deskMat);
      this.desk.position.set(0, -5.55, -1.2);
      this.desk.receiveShadow = true;
      this.scene.add(this.desk);

      const topMat = new THREE.MeshBasicMaterial({ color: 0xeaf5ee, transparent: true, opacity: 0.5, depthWrite: false });
      this.topHaze = new THREE.Mesh(new THREE.PlaneGeometry(30, 1.1), topMat);
      this.topHaze.position.set(0, 5.48, -5.5);
      this.scene.add(this.topHaze);
    }

    updateGroup(group, dt, speed, factor, span) {
      for (let i = 0; i < group.children.length; i += 1) {
        const child = group.children[i];
        child.position.x -= speed * factor * dt;
        if (child.position.x < -span / 2) child.position.x += span;
      }
    }

    update(dt, speed) {
      this.updateGroup(this.far, dt, speed, 0.055, this.farSpan);
      this.updateGroup(this.mid, dt, speed, 0.15, this.midSpan);
      this.updateGroup(this.near, dt, speed, 0.3, this.nearSpan);
    }
  }

  class ObstacleSegment {
    constructor(direction) {
      this.direction = direction;
      this.group = new THREE.Group();

      this.materials = {
        pencil: new THREE.MeshToonMaterial({ color: 0xf3c86b }),
        pencilBand: new THREE.MeshToonMaterial({ color: 0xc17380 }),
        wood: new THREE.MeshToonMaterial({ color: 0xf2dfbd }),
        straw: new THREE.MeshToonMaterial({ color: 0xe5a3aa }),
        strawBand: new THREE.MeshToonMaterial({ color: 0xffd8d1 }),
        circuit: new THREE.MeshToonMaterial({ color: 0x587c7e }),
        circuitChip: new THREE.MeshToonMaterial({ color: 0xc6eff0 }),
        stem: new THREE.MeshToonMaterial({ color: 0x7eb79a }),
        leaf: new THREE.MeshToonMaterial({ color: 0xa4cfaa }),
        book: new THREE.MeshToonMaterial({ color: 0x817995 }),
        bookBand: new THREE.MeshToonMaterial({ color: 0xf0b29c })
      };

      this.boxBody = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 0.78), this.materials.pencil);
      this.cylBody = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 1, 12), this.materials.straw);
      this.group.add(this.boxBody, this.cylBody);

      this.tip = new THREE.Mesh(new THREE.ConeGeometry(0.56, 0.55, 7), this.materials.wood);
      this.group.add(this.tip);

      this.ring = new THREE.Mesh(new THREE.TorusGeometry(0.51, 0.075, 7, 18), this.materials.strawBand);
      this.ring.rotation.x = Math.PI / 2;
      this.group.add(this.ring);

      this.cap = new THREE.Mesh(new THREE.SphereGeometry(0.53, 12, 8), this.materials.leaf);
      this.cap.scale.y = 0.42;
      this.group.add(this.cap);

      this.leaf = new THREE.Mesh(new THREE.SphereGeometry(0.48, 10, 7), this.materials.leaf);
      this.leaf.scale.set(0.9, 0.28, 0.32);
      this.group.add(this.leaf);

      this.chips = new THREE.Group();
      const chipGeo = new THREE.BoxGeometry(0.17, 0.28, 0.12);
      for (let i = 0; i < 3; i += 1) {
        const chip = new THREE.Mesh(chipGeo, this.materials.circuitChip);
        chip.position.set(i % 2 ? -0.23 : 0.22, -0.35 + i * 0.4, 0.47);
        this.chips.add(chip);
      }
      this.group.add(this.chips);

      this.bandA = new THREE.Mesh(new THREE.BoxGeometry(1.14, 0.13, 0.84), this.materials.bookBand);
      this.bandB = new THREE.Mesh(new THREE.BoxGeometry(1.14, 0.13, 0.84), this.materials.bookBand);
      this.group.add(this.bandA, this.bandB);

      this.boxBody.receiveShadow = true;
      this.cylBody.receiveShadow = true;
    }

    setType(type, height) {
      const d = this.direction;
      const endY = d * height * 0.5;
      this.boxBody.visible = false;
      this.cylBody.visible = false;
      this.tip.visible = false;
      this.ring.visible = false;
      this.cap.visible = false;
      this.leaf.visible = false;
      this.chips.visible = false;
      this.bandA.visible = false;
      this.bandB.visible = false;

      if (type === 0) {
        this.boxBody.visible = true;
        this.boxBody.material = this.materials.pencil;
        this.boxBody.scale.set(0.88, height, 1);
        this.tip.visible = true;
        this.tip.position.y = endY + d * 0.25;
        this.tip.rotation.z = d < 0 ? Math.PI : 0;
        this.bandA.visible = true;
        this.bandA.material = this.materials.pencilBand;
        this.bandA.scale.x = 0.8;
        this.bandA.position.y = endY - d * 0.17;
      } else if (type === 1) {
        this.cylBody.visible = true;
        this.cylBody.material = this.materials.straw;
        this.cylBody.scale.set(0.9, height, 0.9);
        this.ring.visible = true;
        this.ring.position.y = endY;
      } else if (type === 2) {
        this.boxBody.visible = true;
        this.boxBody.material = this.materials.circuit;
        this.boxBody.scale.set(1.02, height, 1);
        this.chips.visible = true;
        this.chips.position.y = endY - d * 0.75;
        this.chips.rotation.z = d < 0 ? Math.PI : 0;
      } else if (type === 3) {
        this.cylBody.visible = true;
        this.cylBody.material = this.materials.stem;
        this.cylBody.scale.set(0.57, height, 0.57);
        this.cap.visible = true;
        this.cap.position.y = endY;
        this.leaf.visible = true;
        this.leaf.position.set(d > 0 ? 0.4 : -0.4, endY - d * 0.72, 0.02);
        this.leaf.rotation.z = d > 0 ? 0.58 : -0.58;
      } else {
        this.boxBody.visible = true;
        this.boxBody.material = this.materials.book;
        this.boxBody.scale.set(1.12, height, 1);
        this.bandA.visible = true;
        this.bandB.visible = true;
        this.bandA.material = this.materials.bookBand;
        this.bandB.material = this.materials.bookBand;
        this.bandA.position.y = endY - d * 0.21;
        this.bandB.position.y = endY - d * 0.52;
      }
    }
  }

  class ObstaclePair {
    constructor(scene) {
      this.group = new THREE.Group();
      this.lower = new ObstacleSegment(1);
      this.upper = new ObstacleSegment(-1);
      this.group.add(this.lower.group, this.upper.group);
      scene.add(this.group);
      this.active = false;
      this.scored = false;
      this.gapCenter = 0;
      this.gapSize = CONFIG.obstacleGap;
      this.type = 0;
      this.halfWidth = CONFIG.obstacleWidth * 0.5;
      this.group.visible = false;
    }

    activate(x, gapCenter, gapSize, type) {
      this.active = true;
      this.scored = false;
      this.gapCenter = gapCenter;
      this.gapSize = gapSize;
      this.type = type;
      this.group.visible = true;
      this.group.position.x = x;

      const halfWorld = CONFIG.worldHalfHeight + 0.75;
      const gapBottom = gapCenter - gapSize / 2;
      const gapTop = gapCenter + gapSize / 2;
      const lowerHeight = Math.max(0.8, gapBottom + halfWorld);
      const upperHeight = Math.max(0.8, halfWorld - gapTop);

      this.lower.group.position.y = -halfWorld + lowerHeight / 2;
      this.upper.group.position.y = halfWorld - upperHeight / 2;
      this.lower.setType(type, lowerHeight);
      this.upper.setType(type, upperHeight);
    }

    deactivate() {
      this.active = false;
      this.group.visible = false;
    }
  }

  class ObstacleManager {
    constructor(scene, rendererSystem, onScore) {
      this.scene = scene;
      this.rendererSystem = rendererSystem;
      this.onScore = onScore;
      this.pool = [];
      this.spawnAccumulator = 0;
      this.lastGap = 0;
      this.typeCursor = 0;
      for (let i = 0; i < CONFIG.obstaclePoolSize; i += 1) {
        this.pool.push(new ObstaclePair(scene));
      }
    }

    reset() {
      for (let i = 0; i < this.pool.length; i += 1) this.pool[i].deactivate();
      this.spawnAccumulator = CONFIG.spawnDistance * 0.43;
      this.lastGap = 0;
      this.typeCursor = Math.floor(Math.random() * 5);
    }

    getFree() {
      for (let i = 0; i < this.pool.length; i += 1) {
        if (!this.pool[i].active) return this.pool[i];
      }
      return null;
    }

    spawn(score, xOverride) {
      const pair = this.getFree();
      if (!pair) return;
      const gapSize = Math.max(CONFIG.minObstacleGap, CONFIG.obstacleGap - score * 0.034);
      const allowed = CONFIG.worldHalfHeight - gapSize / 2 - 0.72;
      const drift = clamp(rand(-1.18, 1.18), -1.05, 1.05);
      const target = clamp(this.lastGap + drift, -allowed, allowed);
      const center = lerp(this.lastGap, target, 0.88);
      this.lastGap = center;
      this.typeCursor = (this.typeCursor + 1 + (Math.random() > 0.72 ? 1 : 0)) % 5;
      const x = xOverride == null ? this.rendererSystem.camera.right + 2.0 : xOverride;
      pair.activate(x, center, gapSize, this.typeCursor);
    }

    seed(score) {
      const start = this.rendererSystem.camera.right + 3.3;
      this.spawn(score, start);
      this.spawn(score, start + CONFIG.spawnDistance);
      this.spawn(score, start + CONFIG.spawnDistance * 2);
    }

    update(dt, speed, score, flyX) {
      this.spawnAccumulator += speed * dt;
      if (this.spawnAccumulator >= CONFIG.spawnDistance) {
        this.spawnAccumulator -= CONFIG.spawnDistance;
        this.spawn(score);
      }

      const leftKill = this.rendererSystem.camera.left - 2.5;
      for (let i = 0; i < this.pool.length; i += 1) {
        const p = this.pool[i];
        if (!p.active) continue;
        p.group.position.x -= speed * dt;
        if (!p.scored && p.group.position.x + p.halfWidth < flyX) {
          p.scored = true;
          this.onScore();
        }
        if (p.group.position.x < leftKill) p.deactivate();
      }
    }

    collides(flyX, flyY, radius) {
      for (let i = 0; i < this.pool.length; i += 1) {
        const p = this.pool[i];
        if (!p.active) continue;
        const dx = Math.abs(flyX - p.group.position.x);
        if (dx > p.halfWidth + radius) continue;
        const gapBottom = p.gapCenter - p.gapSize / 2;
        const gapTop = p.gapCenter + p.gapSize / 2;
        if (flyY - radius < gapBottom || flyY + radius > gapTop) return true;
      }
      return false;
    }
  }

  class InputManager {
    constructor(onAction) {
      this.onAction = onAction;
      this.pointer = (e) => {
        if (e.target && (e.target.id === 'retry' || e.target.id === 'soundToggle' || e.target.closest?.('#retry') || e.target.closest?.('#soundToggle'))) return;
        e.preventDefault();
        this.onAction();
      };
      this.key = (e) => {
        if (e.code !== 'Space') return;
        e.preventDefault();
        if (!e.repeat) this.onAction();
      };
      window.addEventListener('pointerdown', this.pointer, { passive: false });
      window.addEventListener('keydown', this.key, { passive: false });
      window.addEventListener('contextmenu', (e) => e.preventDefault());
    }
  }

  class Game {
    constructor() {
      this.rendererSystem = new RendererSystem(document.getElementById('scene'));
      this.audio = new AudioManager();
      this.ui = new UIManager(this.audio);
      this.particles = new ParticleManager(this.rendererSystem.scene);
      this.world = new World(this.rendererSystem.scene);
      this.fly = new Fly(this.rendererSystem.scene, this.particles, this.audio);
      this.obstacles = new ObstacleManager(
        this.rendererSystem.scene,
        this.rendererSystem,
        () => this.addScore()
      );
      this.input = new InputManager(() => this.handleAction());

      this.state = STATE.READY;
      this.score = 0;
      this.best = this.loadBest();
      this.elapsed = 0;
      this.gameOverElapsed = 0;
      this.clock = new THREE.Clock();
      this.lastFrameTime = performance.now();
      this.frameSamples = 0;
      this.frameAccum = 0;
      this.fps = 60;

      this.ui.setBest(this.best);
      this.ui.retryButton.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.audio.ensure();
        this.restart(true);
      });
      this.ui.soundButton.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.audio.ensure();
        this.audio.setMuted(!this.audio.muted);
        this.ui.soundButton.classList.toggle('is-muted', this.audio.muted);
      });

      window.addEventListener('resize', () => this.resize(), { passive: true });
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) this.clock.stop();
        else {
          this.clock.start();
          this.clock.getDelta();
        }
      });

      this.resetReady();
      this.resize();
      this.loop = this.loop.bind(this);
      requestAnimationFrame(this.loop);
    }

    loadBest() {
      try {
        const n = Number(localStorage.getItem('flyBrainBest'));
        return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
      } catch (_) {
        return 0;
      }
    }

    saveBest() {
      try {
        localStorage.setItem('flyBrainBest', String(this.best));
      } catch (_) {}
    }

    resize() {
      this.rendererSystem.resize();
      const c = this.rendererSystem.camera;
      const flyX = c.left + (c.right - c.left) * 0.335;
      this.fly.setX(flyX);
    }

    resetReady() {
      this.state = STATE.READY;
      this.score = 0;
      this.elapsed = 0;
      this.gameOverElapsed = 0;
      this.ui.setScore(0);
      this.ui.showReady();
      this.fly.reset(0);
      this.obstacles.reset();
    }

    start() {
      if (this.state !== STATE.READY) return;
      this.state = STATE.RUNNING;
      this.elapsed = 0;
      this.ui.showRunning();
      this.obstacles.seed(this.score);
    }

    restart(withFlap) {
      this.score = 0;
      this.elapsed = 0;
      this.gameOverElapsed = 0;
      this.ui.setScore(0);
      this.fly.reset(0);
      this.obstacles.reset();
      this.state = STATE.RUNNING;
      this.ui.showRunning();
      this.obstacles.seed(0);
      if (withFlap) this.fly.flap();
    }

    handleAction() {
      this.audio.ensure();
      if (this.state === STATE.READY) {
        this.start();
        this.fly.flap();
      } else if (this.state === STATE.RUNNING) {
        this.fly.flap();
      } else if (this.state === STATE.GAMEOVER && this.gameOverElapsed >= CONFIG.gameOverPanelDelay) {
        this.restart(true);
      }
    }

    addScore() {
      if (this.state !== STATE.RUNNING) return;
      this.score += 1;
      if (this.score > this.best) {
        this.best = this.score;
        this.ui.setBest(this.best);
        this.saveBest();
      }
      this.ui.setScore(this.score);
      this.audio.score();
      this.particles.emitScore(this.fly.root.position.x, this.fly.root.position.y);
    }

    speed() {
      return CONFIG.scrollSpeed + Math.min(
        CONFIG.maxScrollBonus,
        this.score * 0.055 + this.elapsed * 0.011
      );
    }

    hit() {
      if (this.state !== STATE.RUNNING) return;
      this.state = STATE.GAMEOVER;
      this.gameOverElapsed = 0;
      this.fly.crash();
      if (this.score > this.best) {
        this.best = this.score;
        this.saveBest();
        this.ui.setBest(this.best);
      }
    }

    step(dt) {
      const speed = this.speed();
      if (this.state === STATE.RUNNING) {
        this.elapsed += dt;
        this.fly.physics(dt);
        this.world.update(dt, speed);
        this.obstacles.update(dt, speed, this.score, this.fly.root.position.x);
        this.ui.update(dt, true);

        const y = this.fly.root.position.y;
        if (
          y - CONFIG.flyCollisionRadius < -CONFIG.worldHalfHeight + 0.13 ||
          y + CONFIG.flyCollisionRadius > CONFIG.worldHalfHeight - 0.08 ||
          this.obstacles.collides(this.fly.root.position.x, y, CONFIG.flyCollisionRadius)
        ) {
          this.hit();
        }
      } else if (this.state === STATE.GAMEOVER) {
        this.gameOverElapsed += dt;
        this.fly.physics(dt);
        this.world.update(dt, speed * 0.24);
        if (this.gameOverElapsed >= CONFIG.gameOverPanelDelay && this.ui.gameOverPanel.classList.contains('is-hidden')) {
          this.ui.showGameOver(this.score, this.best);
        }
      } else {
        this.world.update(dt, CONFIG.scrollSpeed * 0.08);
      }

      this.fly.animateVisual(dt, this.state === STATE.READY);
      this.particles.update(dt);
    }

    loop(now) {
      requestAnimationFrame(this.loop);
      let dt = this.clock.getDelta();
      if (!Number.isFinite(dt) || dt <= 0) dt = 1 / 60;
      dt = Math.min(dt, CONFIG.maxDelta);

      let remaining = dt;
      while (remaining > 0) {
        const step = Math.min(CONFIG.physicsStepMax, remaining);
        this.step(step);
        remaining -= step;
      }

      this.rendererSystem.render();
      const frameMs = now - this.lastFrameTime;
      this.lastFrameTime = now;
      if (frameMs > 0 && frameMs < 200) {
        this.frameAccum += frameMs;
        this.frameSamples += 1;
        if (this.frameSamples >= 45) {
          this.fps = 1000 / (this.frameAccum / this.frameSamples);
          this.frameSamples = 0;
          this.frameAccum = 0;
        }
      }
    }

    debugCrash() {
      if (this.state === STATE.READY) this.start();
      if (this.state === STATE.RUNNING) this.hit();
    }

    debugScore(value) {
      const target = Math.max(0, Math.floor(value));
      while (this.score < target) this.addScore();
    }

    getMetrics() {
      return {
        state: this.state,
        score: this.score,
        best: this.best,
        fps: Number(this.fps.toFixed(1)),
        drawCalls: this.rendererSystem.renderer.info.render.calls,
        triangles: this.rendererSystem.renderer.info.render.triangles,
        geometries: this.rendererSystem.renderer.info.memory.geometries,
        textures: this.rendererSystem.renderer.info.memory.textures,
        activeObstacles: this.obstacles.pool.filter((p) => p.active).length
      };
    }
  }

  const game = new Game();
  window.__FLY_BRAIN__ = game;
})();
