/* Home's voxel map. Original data and accessible SVG stay in the document.
   A small WebGL2 renderer gathers green particles along the original map border before revealing shallow beveled cubes, with no third-party runtime. */
(function () {
  'use strict';
  var stage = document.querySelector('.hero-map-stage');
  if (!stage) return;
  var svg = stage.querySelector('svg.um');
  var hero = stage.closest('.hero');
  var replay = hero.querySelector('.hero-pause input');
  var ticker = hero.querySelector('.hero-n .tick-anim');
  var year = hero.querySelector('.yr-anim');
  if (!replay || !ticker || !year || !window.ResizeObserver || !window.IntersectionObserver) return;
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var finePointer = matchMedia('(hover: hover) and (pointer: fine)');
  var box = svg.viewBox.baseVal;
  var cells = [], steps = [];
  svg.querySelectorAll('g[class^="s"]').forEach(function (group, step) {
    group.querySelectorAll('rect').forEach(function (rect) {
      var size = rect.width.baseVal.value;
      cells.push([rect.x.baseVal.value + size / 2 + 6, rect.y.baseVal.value + size / 2 + 6, size, cells.length, step]);
    });
    steps.push(cells.length);
  });
  var outlinePath = svg.querySelector('g[transform] > path');
  if (!cells.length || !outlinePath) return;
  var numbers = outlinePath.getAttribute('d').match(/-?\d+(?:\.\d+)?/g).map(Number);
  var outline = [];
  for (var k = 0; k < numbers.length; k += 2) outline.push(numbers[k] + 6, numbers[k + 1] + 6);
  var canvas = document.createElement('canvas');
  canvas.className = 'hero-map-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  stage.appendChild(canvas);
  var gl = canvas.getContext('webgl2', { alpha: true, antialias: true, premultipliedAlpha: true });
  if (!gl) { canvas.remove(); return; }
  var rootStyle = getComputedStyle(document.documentElement);
  function color(token) {
    var hex = rootStyle.getPropertyValue(token).trim().slice(1);
    return [0, 2, 4].map(function (i) { return parseInt(hex.slice(i, i + 2), 16) / 255; });
  }
  var old = color('--cell-old'), mint = color('--mint'), highlight = color('--mint-hi');
  var renderer, frameId = 0, visible = false, lost = false, lastFrame = 0;
  var width = 0, height = 0, scale = 1, pitch = .48, yaw = -.14;
  var pointerX = 0, pointerY = 0, ripples = [], lastPointerTime = 0;
  var motionTime = 0;
  var assemblyElapsed = 0, assemblyDuration = 1600;
  var boundsDirty = true, stageTop = 0;
  var firstYear = Number(hero.getAttribute('data-map-first-year'));
  var latestAccounts = Number(hero.getAttribute('data-map-accounts'));
  var latestYear = Number(hero.getAttribute('data-map-latest-year'));

  // Every program shares this projection; the border, particles and cubes rotate together.
  var projection = 'uniform vec2 uWorld; uniform vec2 uViewport; uniform vec2 uAngle; uniform float uScale;\n' +
    'vec3 rotateMap(vec3 p) { float c=cos(uAngle.x), s=sin(uAngle.x); p=vec3(p.x,p.y*c-p.z*s,p.y*s+p.z*c);' +
    'c=cos(uAngle.y); s=sin(uAngle.y); return vec3(p.x*c+p.z*s,p.y,-p.x*s+p.z*c); }\n' +
    'vec4 projectMap(vec3 p) { p=rotateMap(p); float perspective=1800.0/(1800.0-p.z);' +
    'return vec4(p.x*uScale*perspective*2.0/uViewport.x,-p.y*uScale*perspective*2.0/uViewport.y,-p.z/1200.0,1.0); }\n';
  function shader(type, source) {
    var sh = gl.createShader(type);
    gl.shaderSource(sh, source); gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      var message = gl.getShaderInfoLog(sh); gl.deleteShader(sh); throw new Error(message);
    }
    return sh;
  }
  function program(vertex, fragment) {
    var p = gl.createProgram(), v = shader(gl.VERTEX_SHADER, vertex), f = shader(gl.FRAGMENT_SHADER, fragment);
    gl.attachShader(p, v); gl.attachShader(p, f); gl.linkProgram(p);
    gl.deleteShader(v); gl.deleteShader(f);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { gl.deleteProgram(p); throw new Error('Map shader link failed'); }
    return p;
  }
  // A staggered entrance runs once; subsequent growth loops keep the formed border.
  var formation = 'uniform float uAssembly;\n' +
    'float hash(float n){return fract(sin(n*127.1+311.7)*43758.5453);}' +
    'float assembled(float order){return smoothstep(0.0,1.0,clamp((uAssembly-hash(order)*.15)/.65,0.0,1.0));}\n';
  function createRenderer() {
    var cubes = program('#version 300 es\nprecision highp float;\n' + projection + formation +
      'layout(location=0) in vec3 aPosition; layout(location=1) in vec3 aNormal;' +
      'layout(location=2) in vec3 aCell; layout(location=3) in vec2 aOrder;' +
      'uniform float uCount; uniform float uStep; uniform float uTime; uniform vec4 uRipples[6];' +
      'out vec3 vNormal; out float vNew; out float vWave;\n' +
      'void main(){ float pop=clamp(uCount-aOrder.x,0.0,1.0);' +
      'if(pop<=0.0){gl_Position=vec4(2.0,2.0,2.0,1.0);vNormal=aNormal;vNew=0.0;vWave=0.0;return;}' +
      'float wave=0.0; for(int i=0;i<6;i++){float age=uTime-uRipples[i].z; if(age>=0.0 && age<1.15){' +
      'float d=distance(aCell.xy,uRipples[i].xy); float ring=(d-age*180.0)/42.0;' +
      'wave+=exp(-ring*ring)*exp(-age*3.2)*uRipples[i].w;}}' +
      'wave=min(wave,14.0); float smoothPop=pop*pop*(3.0-2.0*pop)*smoothstep(.82,1.0,uAssembly);' +
      'float depth=9.0+wave+(1.0-smoothPop)*16.0;' +
      'vec3 p=vec3(aCell.xy-uWorld*.5+aPosition.xy*aCell.z*smoothPop,aPosition.z*depth*smoothPop);' +
      'gl_Position=projectMap(p); vNormal=rotateMap(aNormal); vNew=1.0-step(.5,abs(aOrder.y-uStep)); vWave=wave/14.0; }',
      '#version 300 es\nprecision highp float;\n' +
      'uniform vec3 uOld; uniform vec3 uMint; uniform vec3 uHighlight;' +
      'in vec3 vNormal; in float vNew; in float vWave; out vec4 fragColor;\n' +
      'void main(){vec3 n=normalize(vNormal); float light=.57+.43*max(dot(n,normalize(vec3(-.35,-.55,1.0))),0.0);' +
      'vec3 base=mix(uOld,uMint,vNew); base=mix(base,uHighlight,vWave*.35); fragColor=vec4(base*light,1.0); }');
    var line = program('#version 300 es\nprecision highp float;\n' + projection +
      'layout(location=0) in vec2 aPoint; layout(location=1) in vec2 aNext; layout(location=2) in float aSide;' +
      'void main(){vec4 p=projectMap(vec3(aPoint-uWorld*.5,-1.0)); vec4 next=projectMap(vec3(aNext-uWorld*.5,-1.0));' +
      'vec2 direction=normalize((next.xy-p.xy)*uViewport); vec2 normal=vec2(-direction.y,direction.x);' +
      'p.xy+=normal*aSide*1.4/uViewport; gl_Position=p;}',
      '#version 300 es\nprecision highp float;\nuniform vec3 uColor; uniform float uAssembly; out vec4 fragColor;' +
      'void main(){fragColor=vec4(uColor,.55*smoothstep(.78,.96,uAssembly));}');
    var particles = program('#version 300 es\nprecision highp float;\n' + projection + formation +
      'layout(location=0) in vec2 aPoint; layout(location=1) in float aSeed;' +
      'uniform float uDpr; out float vAlpha; out float vTint;\n' +
      'void main(){float progress=assembled(aSeed); float angle=hash(aSeed+3.0)*6.283185;' +
      'vec3 origin=vec3((hash(aSeed+1.0)-.5)*uWorld.x*1.22,(hash(aSeed+2.0)-.5)*uWorld.y*1.10,(hash(aSeed+4.0)-.5)*260.0);' +
      'vec3 target=vec3(aPoint-uWorld*.5,-1.0); vec3 p=mix(origin,target,progress);' +
      'float arc=sin(progress*3.141593); p+=vec3(cos(angle)*32.0,sin(angle)*32.0,70.0)*arc;' +
      'gl_Position=projectMap(p); gl_PointSize=(3.0+hash(aSeed+5.0)*2.0)*uDpr;' +
      'vAlpha=.85*smoothstep(0.0,.12,uAssembly)*(1.0-smoothstep(.82,1.0,uAssembly));' +
      'vTint=.35+hash(aSeed+6.0)*.65;}',
      '#version 300 es\nprecision highp float;\n' +
      'uniform vec3 uMint; uniform vec3 uHighlight; in float vAlpha; in float vTint; out vec4 fragColor;\n' +
      'void main(){float radius=length(gl_PointCoord-vec2(.5))*2.0;' +
      'float glow=1.0-smoothstep(.20,1.0,radius); float alpha=vAlpha*glow;' +
      'if(alpha<.015)discard; fragColor=vec4(mix(uMint,uHighlight,vTint),alpha);}');
    var vertices = [];
    function face(a, b, c, d, normal) {
      [a,b,c,a,c,d].forEach(function (p) { vertices.push.apply(vertices, p.concat(normal)); });
    }
    // An inset top and four bevels catch light without textures or post-processing.
    var b = .5, t = .40, z = .78;
    face([-t,-t,1],[t,-t,1],[t,t,1],[-t,t,1],[0,0,1]);
    face([-b,-b,z],[b,-b,z],[t,-t,1],[-t,-t,1],[0,-.707,.707]);
    face([b,-b,z],[b,b,z],[t,t,1],[t,-t,1],[.707,0,.707]);
    face([b,b,z],[-b,b,z],[-t,t,1],[t,t,1],[0,.707,.707]);
    face([-b,b,z],[-b,-b,z],[-t,-t,1],[-t,t,1],[-.707,0,.707]);
    face([-b,-b,0],[b,-b,0],[b,-b,z],[-b,-b,z],[0,-1,0]);
    face([b,-b,0],[b,b,0],[b,b,z],[b,-b,z],[1,0,0]);
    face([b,b,0],[-b,b,0],[-b,b,z],[b,b,z],[0,1,0]);
    face([-b,b,0],[-b,-b,0],[-b,-b,z],[-b,b,z],[-1,0,0]);
    var cubeVAO = gl.createVertexArray(); gl.bindVertexArray(cubeVAO);
    function buffer(data) {
      var handle = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, handle);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STATIC_DRAW); return handle;
    }
    function attribute(index, count, stride, offset, divisor) {
      gl.enableVertexAttribArray(index); gl.vertexAttribPointer(index,count,gl.FLOAT,false,stride,offset);
      gl.vertexAttribDivisor(index, divisor || 0);
    }
    buffer(vertices); attribute(0,3,24,0); attribute(1,3,24,12);
    var instances = [];
    cells.forEach(function (c) { instances.push.apply(instances,c); });
    buffer(instances); attribute(2,3,20,0,1); attribute(3,2,20,12,1);
    var lineVAO = gl.createVertexArray(); gl.bindVertexArray(lineVAO);
    // A narrow ribbon keeps the outline legible on high-density displays too.
    var borderData = [];
    for (var edge=0;edge<outline.length;edge+=2) {
      var next=(edge+2)%outline.length;
      var a=[outline[edge],outline[edge+1]], b=[outline[next],outline[next+1]];
      if (Math.hypot(a[0]-b[0],a[1]-b[1])<.001) continue;
      var left=a.concat(b,1), right=a.concat(b,-1), endLeft=b.concat(a,-1), endRight=b.concat(a,1);
      [left,right,endRight,left,endRight,endLeft].forEach(function (vertex) { borderData.push.apply(borderData,vertex); });
    }
    buffer(borderData); attribute(0,2,20,0); attribute(1,2,20,8); attribute(2,1,20,16);
    var particleVAO = gl.createVertexArray(); gl.bindVertexArray(particleVAO);
    // Even spacing follows the original SVG border, independently of the account cells.
    var particleData = [], particleCount = 720, perimeter = outlinePath.getTotalLength();
    for (var seed=0;seed<particleCount;seed++) {
      var point=outlinePath.getPointAtLength(perimeter*seed/particleCount);
      particleData.push(point.x+6,point.y+6,seed);
    }
    buffer(particleData); attribute(0,2,12,0); attribute(1,1,12,8);
    gl.bindVertexArray(null);
    var locations = new Map();
    [cubes,line,particles].forEach(function (p) {
      var values = {};
      ['uWorld','uViewport','uAngle','uScale','uCount','uStep','uTime','uRipples[0]','uOld','uMint','uHighlight','uColor','uAssembly','uDpr'].forEach(function (name) {
        values[name]=gl.getUniformLocation(p,name);
      });
      locations.set(p,values);
    });
    var trail = new Float32Array(24);
    function uniforms(p, time, assembly) {
      gl.useProgram(p);
      function u(name) { return locations.get(p)[name]; }
      gl.uniform2f(u('uWorld'),box.width,box.height);
      gl.uniform2f(u('uViewport'),width,height);
      gl.uniform2f(u('uAngle'),pitch,yaw); gl.uniform1f(u('uScale'),scale);
      gl.uniform1f(u('uAssembly'),assembly);
      gl.uniform1f(u('uDpr'),Math.min(devicePixelRatio || 1,2));
      if (p !== line) {
        // Only the cube shader consumes the counters and ripples. Reading them again for
        // the particle shader forced redundant style calculations during the entrance.
        if (p === cubes) {
        var count = Number(getComputedStyle(ticker).getPropertyValue('--tick'));
        var currentYear = Number(getComputedStyle(year).getPropertyValue('--yr'));
        if (!Number.isFinite(count) || !count || !currentYear) { count=latestAccounts; currentYear=latestYear; }
        gl.uniform1f(u('uCount'),Math.min(cells.length,count/1000));
        gl.uniform1f(u('uStep'),Math.max(0,Math.min(steps.length-1,currentYear-firstYear)));
        gl.uniform1f(u('uTime'),time);
        for (var i=0;i<6;i++) {
          var r=ripples[i]; trail.set(r ? [r.x,r.y,r.time,r.strength] : [0,0,-100,0],i*4);
        }
        gl.uniform4fv(u('uRipples[0]'),trail);
        }
        gl.uniform3fv(u('uOld'),old); gl.uniform3fv(u('uMint'),mint); gl.uniform3fv(u('uHighlight'),highlight);
      } else gl.uniform3fv(u('uColor'),highlight);
    }
    return function draw(time, assembly) {
      gl.viewport(0,0,canvas.width,canvas.height);
      gl.enable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
      gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      uniforms(cubes,time,assembly); gl.bindVertexArray(cubeVAO); gl.drawArraysInstanced(gl.TRIANGLES,0,vertices.length/6,cells.length);
      if (assembly<1) {
        gl.depthMask(false);
        uniforms(particles,time,assembly); gl.bindVertexArray(particleVAO);
        gl.drawArrays(gl.POINTS,0,particleCount);
        gl.depthMask(true);
      }
      // Draw the border last, so raised cells never hide the country silhouette.
      gl.disable(gl.DEPTH_TEST);
      uniforms(line,time,assembly); gl.bindVertexArray(lineVAO); gl.drawArrays(gl.TRIANGLES,0,borderData.length/5);
      gl.bindVertexArray(null);
    };
  }
  function wake() {
    if (renderer && !frameId && visible && !lost && !motion.matches && !document.hidden) frameId=requestAnimationFrame(frame);
  }
  function frame(now) {
    frameId=0;
    if (!visible || lost || motion.matches || document.hidden) return;
    var elapsed=Math.min(64,now-(lastFrame || now)); lastFrame=now;
    if (boundsDirty) { stageTop=stage.getBoundingClientRect().top; boundsDirty=false; }
    var progress=Math.max(0,Math.min(1,(innerHeight-stageTop)/(innerHeight*.88)));
    var targetPitch=.24+.56*(1-progress)+pointerY*.035;
    var targetYaw=-.10-.10*(1-progress)+pointerX*.045;
    var ease=1-Math.exp(-elapsed/110);
    pitch+=(targetPitch-pitch)*ease; yaw+=(targetYaw-yaw)*ease;
    var running=replay.checked && !hero.classList.contains('hero-idle');
    if (running) motionTime+=elapsed/1000;
    var time=motionTime;
    ripples=ripples.filter(function (r) { return time-r.time<1.15; });
    if (running) assemblyElapsed=Math.min(assemblyDuration,assemblyElapsed+elapsed);
    renderer(time,assemblyElapsed/assemblyDuration);
    if (!stage.classList.contains('map-ready')) stage.classList.add('map-ready');
    if (running ||
        Math.abs(targetPitch-pitch)+Math.abs(targetYaw-yaw)>.0003) wake();
  }
  function resize() {
    var rect=stage.getBoundingClientRect(); width=rect.width; height=rect.height;
    stageTop=rect.top; boundsDirty=false;
    var dpr=Math.min(devicePixelRatio || 1,2);
    canvas.width=Math.round(width*dpr); canvas.height=Math.round(height*dpr);
    scale=Math.min((width-12)/box.width,(height-12)/box.height)*1.015;
    wake();
  }
  function initialise() {
    if (renderer || lost || motion.matches) return;
    try {
      renderer=createRenderer(); resize();
      // Start empty when first visible; preserve the one-time formation and growth loop.
      renderer(0,0); stage.classList.add('map-ready');
    } catch (err) { lost=true; canvas.remove(); }
  }
  if (stage.getBoundingClientRect().top < innerHeight) initialise();
  new ResizeObserver(resize).observe(stage);
  new IntersectionObserver(function (entries) {
    visible=entries[entries.length-1].isIntersecting;
    lastFrame=0;
    if (visible) { initialise(); wake(); } else { cancelAnimationFrame(frameId); frameId=0; ripples=[]; }
  }).observe(stage);
  window.addEventListener('scroll',function () { boundsDirty=true; wake(); },{passive:true});
  replay.addEventListener('change',function () {
    lastFrame=0;
    wake();
  });
  document.addEventListener('visibilitychange',function () { lastFrame=0; wake(); });
  motion.addEventListener('change',function () {
    if (motion.matches) { cancelAnimationFrame(frameId); frameId=0; ripples=[]; assemblyElapsed=assemblyDuration; stage.classList.remove('map-ready'); }
    else { lastFrame=0; if (visible) initialise(); wake(); }
  });
  canvas.addEventListener('pointermove',function (event) {
    if (!replay.checked || !finePointer.matches || motion.matches || assemblyElapsed<assemblyDuration) return;
    var rect=canvas.getBoundingClientRect();
    pointerX=(event.clientX-rect.left)/width*2-1; pointerY=(event.clientY-rect.top)/height*2-1;
    var now=performance.now();
    if (now-lastPointerTime>85) {
      ripples.push({x:box.width/2+pointerX*width/(2*scale),y:box.height/2+pointerY*height/(2*scale*Math.cos(pitch)),
                    time:motionTime,strength:8});
      if (ripples.length>6) ripples.shift(); lastPointerTime=now;
    }
    wake();
  },{passive:true});
  canvas.addEventListener('pointerleave',function () { pointerX=pointerY=0; wake(); });
  canvas.addEventListener('webglcontextlost',function (event) {
    event.preventDefault(); lost=true; cancelAnimationFrame(frameId); frameId=0; stage.classList.remove('map-ready');
  });
  canvas.addEventListener('webglcontextrestored',function () {
    try { renderer=createRenderer(); lost=false; lastFrame=0; resize(); wake(); } catch (err) { stage.classList.remove('map-ready'); }
  });
})();
