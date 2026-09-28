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

let manifest,positions,current,fac,frameIndex=0,loadToken=0,loading=false,playing=false,lastAdvance=0;
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
  currentLines=new THREE.LineSegments(geometry,currentMaterial);scene.add(currentLines);
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
  $('#status').textContent='Sampled GAMERA volume current + REMIX field-aligned current';
}

async function loadFrame(index){
  frameIndex=Math.max(0,Math.min(manifest.frame_count-1,index));$('#time').value=frameIndex;const token=++loadToken,frame=manifest.frames[frameIndex];loading=true;$('#status').textContent='Loading model frame…';
  try{const [nextCurrent,nextFac]=await Promise.all([binary(frame.current),binary(frame.fac)]);if(token!==loadToken)return;current=nextCurrent;fac=nextFac;loading=false;updateDisplay();}catch(error){if(token===loadToken){loading=false;$('#status').textContent=`Unable to load frame: ${error.message}`;console.error(error);}}
}

function view(name){const settings={global:[[-7,0,0],[30,35,25]],north:[[0,0,0],[.7,-1.4,5]],south:[[0,0,0],[.7,1.4,-5]],tail:[[-15,0,0],[-43,-31,20]]};const [target,pos]=settings[name];controls.target.set(...target);camera.position.set(...pos);controls.update();document.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===name)));}
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>view(button.dataset.view));$('#reset').onclick=()=>view('global');
$('#time').addEventListener('input',event=>loadFrame(+event.target.value));
$('#threshold').addEventListener('input',event=>{$('#threshold-value').textContent=`${event.target.value}% of p99`;updateDisplay();});
$('#scale').addEventListener('input',event=>{$('#scale-value').textContent=`${(+event.target.value/100).toFixed(2)}×`;updateDisplay();});
$('#mhd').onchange=event=>currentLines.visible=event.target.checked;$('#fac-north').onchange=event=>facNorth.visible=event.target.checked;$('#fac-south').onchange=event=>facSouth.visible=event.target.checked;$('#grid').onchange=event=>grid.visible=event.target.checked;
$('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Pause':'Play';};
function resize(){const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}addEventListener('resize',resize);resize();view('global');
function animate(now){controls.update();if(playing&&!loading&&now-lastAdvance>240){lastAdvance=now;loadFrame((frameIndex+1)%manifest.frame_count);}for(const item of labels){const p=item.p.clone().project(camera);item.el.hidden=p.z<-1||p.z>1||Math.abs(p.x)>1||Math.abs(p.y)>1;item.el.style.left=`${(p.x+1)*viewport.clientWidth/2}px`;item.el.style.top=`${(1-p.y)*viewport.clientHeight/2}px`;}renderer.render(scene,camera);requestAnimationFrame(animate);}requestAnimationFrame(animate);

let facPositions;
Promise.all([fetch('manifest.json').then(response=>{if(!response.ok)throw Error(`manifest HTTP ${response.status}`);return response.json();})]).then(async values=>{
  manifest=values[0];[positions,facPositions]=await Promise.all([binary(manifest.positions),binary(manifest.fac_positions)]);$('#time').max=manifest.frame_count-1;setupGeometry();await loadFrame(0);
}).catch(error=>{$('#status').textContent=`Unable to load GAMERA product: ${error.message}`;console.error(error);});
