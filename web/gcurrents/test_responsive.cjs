// Run with NODE_PATH pointing to the bundled Playwright installation.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.VIEWERS_URL||'http://127.0.0.1:8165';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  for(const route of ['currents','gcurrents'])for(const [width,height] of [[390,844],[320,568],[844,390],[1280,800]]){
   const page=await browser.newPage({viewport:{width,height},isMobile:width<900,hasTouch:true,deviceScaleFactor:2});
   const errors=[];page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(`${base}/${route}/`);
   await page.waitForFunction(route=>route==='currents'?document.querySelector('#selected').textContent.includes('illustrative current'):document.querySelector('#viewport').getAttribute('aria-busy')==='false',route);
   assert(await page.locator('#settings').isHidden());
   assert.equal(await page.locator('canvas').count(),1);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   const gear=page.getByRole('button',{name:'Current display settings'});
   const box=await gear.boundingBox();assert(box.width>=44&&box.height>=44);
   await page.screenshot({path:`/tmp/${route}-phone-${width}.png`});
   await gear.tap();assert(await page.locator('#settings').isVisible());
   const panel=await page.locator('#settings').boundingBox();assert(panel.x>=0&&panel.y>=0&&panel.x+panel.width<=width&&panel.y+panel.height<=height);
   const check=page.getByRole('checkbox',{name:'Ring current',exact:true});await check.uncheck();assert(await page.locator('[data-legend="ring"]').evaluate(e=>e.classList.contains('inactive')));await check.check();
   if(route==='gcurrents'){
    const slider=page.getByRole('slider',{name:'GAMERA snapshot'});await slider.press('End');await page.getByText('24:00 into run · 10 / 10',{exact:true}).waitFor();
    await slider.press('Home');await page.getByText('02:00 into run · 1 / 10',{exact:true}).waitFor();
   }else{
    await page.getByRole('checkbox',{name:'Region 1',exact:true}).uncheck();await page.getByRole('checkbox',{name:'Region 1',exact:true}).check();
    await page.getByText('Views & reference layers',{exact:true}).click();await page.locator('#preset').selectOption('1');await page.getByRole('button',{name:'Figure 7 · R1 / Chapman–Ferraro',exact:true}).click();
   }
   await page.screenshot({path:`/tmp/${route}-settings-${width}.png`});
   await gear.tap();assert(await page.locator('#settings').isHidden());
   await page.setViewportSize({width:height,height:width});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   assert.deepEqual(errors,[]);console.log('PASS',route,width,height,'layout, controls, rotation, console');await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
