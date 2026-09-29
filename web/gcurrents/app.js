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

let manifest,positions,current,fac,frameIndex=0,loadToken=0,loading=false,playing=true;
let snapshots=[],snapshotData,pathObjects=[],markers=[],selectedPath=-1,phase=0;
const pathsGroup=new THREE.Group();scene.add(pathsGroup);
const pathColors={dayside:0x4ddf94,tail:0x68adff,ring:0xe68de8,r1:0xff6c77,r2:0x53e3d3};
const groupNames={dayside:'Dayside',tail:'Tail',ring:'Ring region · westward J',r1:'R1-like seeds',r2:'R2-like seeds'};
const arrowUp=new THREE.Vector3(0,1,0);
let currentLines,facNorth,facSouth;
const currentMaterial=new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:.82});
const facMaterial=()=>new THREE.PointsMaterial({size:.055,vertexColors:true,transparent:true,opacity:.92,sizeAttenuation:true});

async function binary(url){const response=await fetch(url);if(!response.ok)throw Error(`${url}: HTTP ${response.status}`);return new Float32Array(await response.arrayBuffer());}
function ramp(t){t=Math.max(0,Math.min(1,t));return new THREE.Color().setRGB(.18+.82*t,.72+.18*t,.78-.55*t);}
function facColor(value,scale){const a=Math.min(1,Math.abs(value)/(scale||1));return value>=0?new THREE.Color(1,.72-.45*a,.72-.42*a):new THREE.Color(.65-.35*a,.76-.38*a,1);}

function setupGeometry(){
  const n=manifest.position_count,geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(n*2*3),3));
  geometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(n*2*3),3));
  currentLines=new THREE.LineSegments(geometry,currentMaterial);currentLines.visible=false;scene.add(currentLines);
  const half=manifest.hemisphere_fac_count;
  function points(offset){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(facPositions.slice(offset*3,(offset+half)*3),3));g.setAttribute('color',new THREE.BufferAttribute(new Float32Array(half*3),3));return new THREE.Points(g,facMaterial());}
  facNorth=points(0);facSouth=points(half);scene.add(facNorth,facSouth);
}

function updateDisplay(){
  if(!current||!fac)return;
  const frame=manifest.frames[frameIndex],p99=frame.current_p99_nA_m2||1,cut=p99*(+$('#threshold').value/100),lengthScale=+$('#scale').value/100;
  const pa=currentLines.geometry.attributes.position.array,ca=currentLines.geometry.attributes.color.array;
  for(let i=0;i<manifest.position_count;i++){
    const p=3*i,j=3*i,ox=positions[p],oy=positions[p+1],oz=positions[p+2],jx=current[j],jy=current[j+1],jz=current[j+2],mag=Math.hypot(jx,jy,jz);
    const q=6*i;pa[q]=ox;pa[q+1]=oy;pa[q+2]=oz;
    if(!Number.isFinite(mag)||mag<cut){pa[q+3]=ox;pa[q+4]=oy;pa[q+5]=oz;}else{const len=lengthScale*(.08+1.05*Math.sqrt(Math.min(mag/p99,2.5))),inv=len/(mag||1);pa[q+3]=ox+jx*inv;pa[q+4]=oy+jy*inv;pa[q+5]=oz+jz*inv;}
    const color=ramp(Math.sqrt(Math.min(mag/p99,1)));for(let k=0;k<2;k++){ca[q+3*k]=color.r;ca[q+3*k+1]=color.g;ca[q+3*k+2]=color.b;}
  }
  currentLines.geometry.attributes.position.needsUpdate=true;currentLines.geometry.attributes.color.needsUpdate=true;currentLines.geometry.computeBoundingSphere();
  const scale=frame.fac_abs_p99_uA_m2||1,half=manifest.hemisphere_fac_count;
  for(const [object,offset] of [[facNorth,0],[facSouth,half]]){const colors=object.geometry.attributes.color.array;for(let i=0;i<half;i++){const color=facColor(fac[offset+i],scale);colors[3*i]=color.r;colors[3*i+1]=color.g;colors[3*i+2]=color.b;}object.geometry.attributes.color.needsUpdate=true;}
  $('#timestamp').textContent=new Date(frame.utc).toLocaleString('en-GB',{timeZone:'UTC',dateStyle:'medium',timeStyle:'short'})+' UTC';
  $('#elapsed').textContent=`t = ${(frame.model_time_s/3600).toFixed(2)} h · frame ${frameIndex+1}/${manifest.frame_count}`;
  $('#j-p99').textContent=`${p99.toPrecision(3)} nA m⁻²`;$('#fac-p99').textContent=`${scale.toPrecision(3)} µA m⁻²`;$('#cpcp').textContent=`${frame.north_cpcp_kV.toFixed(1)} / ${frame.south_cpcp_kV.toFixed(1)} kV`;
  if(!snapshotData)$('#status').textContent='Loading frozen current paths…';
}

async function loadFrame(index){
  frameIndex=Math.max(0,Math.min(manifest.frame_count-1,index));const token=++loadToken,frame=manifest.frames[frameIndex];loading=true;$('#status').textContent='Loading model snapshot…';
  try{const [nextCurrent,nextFac]=await Promise.all([binary(frame.current),binary(frame.fac)]);if(token!==loadToken)return;current=nextCurrent;fac=nextFac;loading=false;updateDisplay();}catch(error){if(token===loadToken){loading=false;$('#status').textContent=`Unable to load frame: ${error.message}`;console.error(error);}}
}

function view(name){const settings={global:[[-7,0,0],[30,35,25]],north:[[0,0,0],[.7,-1.4,5]],south:[[0,0,0],[.7,1.4,-5]],tail:[[-15,0,0],[-43,-31,20]]};const [target,pos]=settings[name];controls.target.set(...target);camera.position.set(...pos);controls.update();document.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===name)));}
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>view(button.dataset.view));$('#reset').onclick=()=>view('global');
function pathVisibility(){
  const group=$('#seed-group').value;
  const limit=+$('#path-count').value,counts={};const shown=new Set();
  for(const obj of pathObjects){const rank=counts[obj.record.group]??0;counts[obj.record.group]=rank+1;const allowed=selectedPath>=0?obj.record.id===selectedPath:(group==='all'||obj.record.group===group)&&rank<limit;obj.mesh.visible=allowed;if(allowed)shown.add(obj.record.id);obj.mesh.material.opacity=.92;obj.mesh.material.color.setHex(obj.record.id===selectedPath?0xffdf89:pathColors[obj.record.group]);}
  for(const m of markers)m.arrow.visible=shown.has(m.id);
  $('#focus-path').disabled=selectedPath<0;
  const record=snapshotData?.paths.find(p=>p.id===selectedPath);
  for(const option of $('#path-choice').options)option.hidden=option.value!=='-1'&&group!=='all'&&option.dataset.group!==group;
  $('#status').textContent=record?`${groupNames[record.group]} · path ${record.id+1} · ${record.length.toFixed(1)} Rᴇ · ${record.start} → ${record.end}`:`${shown.size} visible / ${snapshotData?.paths.length??0} traced paths · frozen GAMERA J · click a path to isolate it`;
}
function selectPath(id){selectedPath=id;$('#path-choice').value=String(id);pathVisibility();}
function buildPaths(record){
  pathsGroup.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});pathsGroup.clear();pathObjects=[];markers=[];selectedPath=-1;
  $('#path-choice').innerHTML='<option value="-1">All paths</option>';
  for(const p of record.paths){
    const pts=p.points.map(q=>new THREE.Vector3(...q)),curve=new THREE.CurvePath();
    for(let i=1;i<pts.length;i++)curve.add(new THREE.LineCurve3(pts[i-1],pts[i]));
    const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,Math.min(1200,pts.length),.045,5,false),new THREE.MeshBasicMaterial({color:pathColors[p.group],transparent:true,opacity:.92}));
    mesh.userData.pathId=p.id;pathsGroup.add(mesh);pathObjects.push({mesh,curve,record:p});
    const count=Math.max(2,Math.min(12,Math.ceil(p.length/6)));
    for(let i=0;i<count;i++){const arrow=new THREE.Mesh(new THREE.ConeGeometry(.16,.52,8),new THREE.MeshBasicMaterial({color:pathColors[p.group]}));pathsGroup.add(arrow);markers.push({arrow,curve,offset:i/count,id:p.id,group:p.group});}
    const option=document.createElement('option');option.value=p.id;option.dataset.group=p.group;option.textContent=`${groupNames[p.group]} · ${p.id+1}${p.start==='inner boundary'&&p.end==='inner boundary'?' · boundary ↔ boundary':''}`;$('#path-choice').append(option);
  }
  pathVisibility();
}
let snapshotToken=0;
async function loadSnapshot(index){
  const token=++snapshotToken;$('#status').textContent='Tracing data loading…';
  try{const response=await fetch(snapshots[index].file+'?v=current-families-3');if(!response.ok)throw Error(`paths HTTP ${response.status}`);const record=await response.json();if(token!==snapshotToken)return;
    await loadFrame(record.frame);if(token!==snapshotToken)return;snapshotData=record;buildPaths(record);
  }catch(error){$('#status').textContent=`Unable to load paths: ${error.message}`;console.error(error);}
}
$('#time').addEventListener('input',event=>loadSnapshot(+event.target.value));
$('#seed-group').onchange=()=>selectPath(-1);$('#path-choice').onchange=e=>selectPath(+e.target.value);
$('#path-count').oninput=e=>{$('#path-count-value').textContent=e.target.value;pathVisibility();};
$('#ring-view').onclick=()=>{$('#seed-group').value='ring';$('#path-count').value=12;$('#path-count-value').textContent='12';selectPath(-1);controls.target.set(0,0,0);camera.position.set(14,16,15);controls.update();};
$('#focus-path').onclick=()=>{const item=pathObjects.find(p=>p.record.id===selectedPath);if(!item)return;const box=new THREE.Box3().setFromObject(item.mesh);box.expandByPoint(new THREE.Vector3(-2.2,-2.2,-2.2));box.expandByPoint(new THREE.Vector3(2.2,2.2,2.2));const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3()).length();const direction=camera.position.clone().sub(controls.target).normalize();controls.target.copy(center);camera.position.copy(center).addScaledVector(direction,Math.max(8,size*1.6));controls.update();};
$('#follow-inner').onclick=()=>{const choices=snapshotData?.paths.filter(p=>p.start==='inner boundary'&&p.end==='inner boundary').sort((a,b)=>a.length-b.length)||[];const p=choices[0]||snapshotData?.paths.find(p=>p.group==='r1'||p.group==='r2');if(p){selectPath(p.id);$('#focus-path').click();}};
const raycaster=new THREE.Raycaster();let pointerStart;
renderer.domElement.addEventListener('pointerdown',e=>pointerStart=[e.clientX,e.clientY]);
renderer.domElement.addEventListener('pointerup',e=>{if(!pointerStart||Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1])>5)return;const r=renderer.domElement.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2(2*(e.clientX-r.left)/r.width-1,1-2*(e.clientY-r.top)/r.height),camera);const hit=raycaster.intersectObjects(pathObjects.filter(p=>p.mesh.visible).map(p=>p.mesh))[0];if(hit)selectPath(hit.object.userData.pathId);});
$('#threshold').addEventListener('input',event=>{$('#threshold-value').textContent=`${event.target.value}% of p99`;updateDisplay();});
$('#scale').addEventListener('input',event=>{$('#scale-value').textContent=`${(+event.target.value/100).toFixed(2)}×`;updateDisplay();});
$('#mhd').onchange=event=>currentLines.visible=event.target.checked;$('#fac-north').onchange=event=>facNorth.visible=event.target.checked;$('#fac-south').onchange=event=>facSouth.visible=event.target.checked;$('#grid').onchange=event=>grid.visible=event.target.checked;
$('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Pause arrows':'Animate arrows';};
function resize(){const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}addEventListener('resize',resize);resize();view('global');
let lastTime=performance.now();function animate(now){const dt=Math.min(.05,(now-lastTime)/1000);lastTime=now;if(playing)phase=(phase+dt*.035)%1;controls.update();for(const m of markers){if(!m.arrow.visible)continue;const u=(phase+m.offset)%1;m.arrow.position.copy(m.curve.getPointAt(u));m.arrow.quaternion.setFromUnitVectors(arrowUp,m.curve.getTangentAt(u).normalize());}for(const item of labels){const p=item.p.clone().project(camera);item.el.hidden=p.z<-1||p.z>1||Math.abs(p.x)>1||Math.abs(p.y)>1;item.el.style.left=`${(p.x+1)*viewport.clientWidth/2}px`;item.el.style.top=`${(1-p.y)*viewport.clientHeight/2}px`;}renderer.render(scene,camera);requestAnimationFrame(animate);}requestAnimationFrame(animate);

let facPositions;
Promise.all([fetch('manifest.json').then(response=>{if(!response.ok)throw Error(`manifest HTTP ${response.status}`);return response.json();})]).then(async values=>{
  manifest=values[0];[positions,facPositions,snapshots]=await Promise.all([binary(manifest.positions),binary(manifest.fac_positions),fetch('snapshots.json?v=current-families-3').then(r=>r.json())]);$('#time').max=snapshots.length-1;$('#time').value=1;setupGeometry();await loadSnapshot(1);if(new URLSearchParams(location.search).get('group')==='ring')$('#ring-view').click();
}).catch(error=>{$('#status').textContent=`Unable to load GAMERA product: ${error.message}`;console.error(error);});
