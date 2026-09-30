import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

const $=selector=>document.querySelector(selector),viewport=$('#viewport');
const scene=new THREE.Scene();scene.background=new THREE.Color(0x061017);scene.fog=new THREE.FogExp2(0x061017,.006);
const camera=new THREE.PerspectiveCamera(42,1,.05,300);camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,2));viewport.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=2;controls.maxDistance=150;
scene.add(new THREE.AmbientLight(0x86aebb,1.3));const sunlight=new THREE.DirectionalLight(0xdff5ff,2.2);sunlight.position.set(18,-4,7);scene.add(sunlight);
const earth=new THREE.Mesh(new THREE.SphereGeometry(1,64,40),new THREE.MeshPhongMaterial({color:0x123c53,emissive:0x03131b,shininess:25}));scene.add(earth);
const glow=new THREE.Mesh(new THREE.SphereGeometry(1.035,64,40),new THREE.MeshBasicMaterial({color:0x3da8c2,transparent:true,opacity:.08,side:THREE.BackSide}));scene.add(glow);

function makeLine(points,color,opacity=.3){return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p))),new THREE.LineBasicMaterial({color,transparent:true,opacity}));}
const grid=new THREE.Group();scene.add(grid);
for(let lat=-75;lat<=75;lat+=15){const a=THREE.MathUtils.degToRad(lat),pts=[];for(let j=0;j<=120;j++){const t=j/120*2*Math.PI;pts.push([1.008*Math.cos(a)*Math.cos(t),1.008*Math.cos(a)*Math.sin(t),1.008*Math.sin(a)]);}grid.add(makeLine(pts,0x56808a,.25));}
for(let lon=0;lon<360;lon+=30){const t=THREE.MathUtils.degToRad(lon),pts=[];for(let j=0;j<=80;j++){const a=-Math.PI/2+j/80*Math.PI;pts.push([1.008*Math.cos(a)*Math.cos(t),1.008*Math.cos(a)*Math.sin(t),1.008*Math.sin(a)]);}grid.add(makeLine(pts,0x56808a,.25));}
const labels=[];function label(text,p){const el=document.createElement('span');el.className='axis-label';el.textContent=text;viewport.append(el);labels.push({el,p:new THREE.Vector3(...p)});}
for(const [text,p] of [['SUN · +X',[15,0,0]],['DUSK · +Y',[0,15,0]],['NORTH · +Z',[0,0,13]],['TAIL',[-40,0,0]]]){grid.add(makeLine([[0,0,0],p],0x34535e,.3));label(text,p);}
for(const r of [5,10,20,30,40]){const pts=[];for(let j=0;j<=160;j++)pts.push([r*Math.cos(j/160*2*Math.PI),r*Math.sin(j/160*2*Math.PI),0]);grid.add(makeLine(pts,0x294651,.18));}

const pathColors={dayside:0x4ddf94,tail:0x68adff,ring:0xe68de8,r1:0xff6c77,r2:0x53e3d3};
const names={dayside:'Dayside',tail:'Tail current',ring:'Ring current',r1:'Region 1-like',r2:'Region 2-like',fac:'Ionospheric FAC'};
const enabled=Object.fromEntries(Object.keys(names).map(k=>[k,true]));
const pathsGroup=new THREE.Group();scene.add(pathsGroup);
const arrowUp=new THREE.Vector3(0,1,0);
let snapshots=[],pathObjects=[],markers=[],facNorth,facSouth,phase=0,snapshotToken=0,facPositions;
const PATHS_PER_TYPE=8;
for(const [kind,name] of Object.entries(names)){
  const color=kind==='fac'?'linear-gradient(90deg,#739aff,#ff6c77)':'#'+pathColors[kind].toString(16);
  const row=document.createElement('label');row.className='current-toggle';
  row.innerHTML='<input type="checkbox" checked data-current="'+kind+'"><i style="background:'+color+'"></i><span>'+name+'</span>';
  $('#current-toggles').append(row);
  const item=document.createElement('span');item.dataset.legend=kind;
  item.innerHTML='<i style="background:'+color+'"></i>'+name;$('#legend').append(item);
  row.querySelector('input').addEventListener('change',event=>{enabled[kind]=event.target.checked;updateVisibility();});
}
function updateVisibility(){
  for(const p of pathObjects)p.mesh.visible=enabled[p.group];
  for(const m of markers)m.arrow.visible=enabled[m.group];
  if(facNorth){facNorth.visible=facSouth.visible=enabled.fac;}
  for(const item of $('#legend').children)item.classList.toggle('inactive',!enabled[item.dataset.legend]);
}
function setPanel(open){$('#settings').hidden=!open;$('#gear').setAttribute('aria-expanded',String(open));}
$('#gear').onclick=()=>setPanel($('#settings').hidden);
document.addEventListener('keydown',event=>{if(event.key==='Escape'){setPanel(false);$('#gear').focus();}});
document.addEventListener('pointerdown',event=>{if(!$('#settings').contains(event.target)&&!$('#gear').contains(event.target))setPanel(false);});

async function binary(url){const response=await fetch(url);if(!response.ok)throw Error('Data HTTP '+response.status);return new Float32Array(await response.arrayBuffer());}
function setupFac(){
  const half=facPositions.length/6;
  function points(offset){
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.BufferAttribute(facPositions.slice(offset*3,(offset+half)*3),3));
    g.setAttribute('color',new THREE.BufferAttribute(new Float32Array(half*3),3));
    return new THREE.Points(g,new THREE.PointsMaterial({size:.055,vertexColors:true,transparent:true,opacity:.92}));
  }
  facNorth=points(0);facSouth=points(half);scene.add(facNorth,facSouth);
}
function updateFac(values){
  const sorted=values.map(Math.abs).sort((a,b)=>a-b),scale=sorted[Math.floor(sorted.length*.99)]||1,half=values.length/2;
  for(const [object,offset] of [[facNorth,0],[facSouth,half]]){
    const colors=object.geometry.attributes.color.array;
    for(let i=0;i<half;i++){
      const value=values[offset+i],a=Math.min(1,Math.abs(value)/scale);
      const color=value>=0?new THREE.Color(1,.72-.45*a,.72-.42*a):new THREE.Color(.65-.35*a,.76-.38*a,1);
      colors[3*i]=color.r;colors[3*i+1]=color.g;colors[3*i+2]=color.b;
    }
    object.geometry.attributes.color.needsUpdate=true;
  }
}
function buildPaths(record){
  pathsGroup.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});
  pathsGroup.clear();pathObjects=[];markers=[];
  const counts={};
  for(const p of record.paths){
    counts[p.group]=(counts[p.group]||0)+1;if(counts[p.group]>PATHS_PER_TYPE)continue;
    const pts=p.points.map(q=>new THREE.Vector3(...q)),curve=new THREE.CurvePath();
    for(let i=1;i<pts.length;i++)curve.add(new THREE.LineCurve3(pts[i-1],pts[i]));
    const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,Math.min(1200,pts.length),.045,5,false),new THREE.MeshBasicMaterial({color:pathColors[p.group],transparent:true,opacity:.92}));
    pathsGroup.add(mesh);pathObjects.push({mesh,group:p.group});
    const count=Math.max(2,Math.min(12,Math.ceil(p.length/6)));
    for(let i=0;i<count;i++){
      const arrow=new THREE.Mesh(new THREE.ConeGeometry(.16,.52,8),new THREE.MeshBasicMaterial({color:pathColors[p.group]}));
      pathsGroup.add(arrow);markers.push({arrow,curve,offset:i/count,group:p.group});
    }
  }
  updateFac(record.fac);updateVisibility();
}
function elapsed(seconds){const minutes=Math.round(seconds/60);return String(Math.floor(minutes/60)).padStart(2,'0')+':'+String(minutes%60).padStart(2,'0');}
async function loadSnapshot(index){
  const token=++snapshotToken;$('#load-error').hidden=true;$('#timestamp').textContent='Loading snapshot '+(index+1)+'…';$('#viewport').setAttribute('aria-busy','true');
  try{
    const response=await fetch(snapshots[index].file+'?v=ten-snapshots-3');if(!response.ok)throw Error('Snapshot HTTP '+response.status);
    const record=await response.json();if(token!==snapshotToken)return;
    buildPaths(record);
    $('#timestamp').textContent=new Date(record.utc).toLocaleString('en-GB',{timeZone:'UTC',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})+' UTC';
    $('#elapsed').textContent=elapsed(record.model_time_s)+' into run · '+(index+1)+' / '+snapshots.length;
    $('#time').setAttribute('aria-valuetext','Snapshot '+(index+1)+' of '+snapshots.length+', '+elapsed(record.model_time_s)+' into run');
    $('#viewport').setAttribute('aria-busy','false');
  }catch(error){
    if(token!==snapshotToken)return;
    $('#timestamp').textContent='Snapshot unavailable';$('#load-error').textContent='Unable to load current paths. Please reload the page.';$('#load-error').hidden=false;
    $('#viewport').setAttribute('aria-busy','false');console.error(error);
  }
}
$('#time').addEventListener('input',event=>loadSnapshot(+event.target.value));
function resize(){const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}
addEventListener('resize',resize);resize();controls.target.set(-7,0,0);camera.position.set(34,46,30);controls.update();
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
let lastTime=performance.now();
function animate(now){
  const dt=Math.min(.05,(now-lastTime)/1000);lastTime=now;if(!reducedMotion.matches)phase=(phase+dt*.035)%1;controls.update();
  for(const m of markers){if(!m.arrow.visible)continue;const u=(phase+m.offset)%1;m.arrow.position.copy(m.curve.getPointAt(u));m.arrow.quaternion.setFromUnitVectors(arrowUp,m.curve.getTangentAt(u).normalize());}
  for(const item of labels){const p=item.p.clone().project(camera);item.el.hidden=p.z<-1||p.z>1||Math.abs(p.x)>1||Math.abs(p.y)>1;item.el.style.left=(p.x+1)*viewport.clientWidth/2+'px';item.el.style.top=(1-p.y)*viewport.clientHeight/2+'px';}
  renderer.render(scene,camera);requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
Promise.all([fetch('snapshots.json?v=ten-snapshots-3').then(r=>{if(!r.ok)throw Error('Snapshot manifest HTTP '+r.status);return r.json();}),binary('fac-positions.bin')]).then(async values=>{
  [snapshots,facPositions]=values;$('#time').max=snapshots.length-1;setupFac();
  // Keep existing shared family links useful with the simplified checkbox UI.
  const group=new URLSearchParams(location.search).get('group');
  if(group in pathColors){for(const kind of Object.keys(pathColors)){enabled[kind]=kind===group;document.querySelector('[data-current="'+kind+'"]').checked=enabled[kind];}}
  const initial=Math.floor((snapshots.length-1)/2);$('#time').value=initial;await loadSnapshot(initial);
}).catch(error=>{$('#load-error').textContent='Unable to load current data. Please reload the page.';$('#load-error').hidden=false;console.error(error);});
