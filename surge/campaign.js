import {Field,W,H} from './engine.js';
export const ENCOUNTERS=[
 {name:'First pulse',short:'First pulse',goal:'Read the front. Find the safe wake behind it.',type:'rings'},
 {name:'Conduction block',short:'Conduction block',goal:'Cut a passage, then commit to crossing it.',type:'wall'},
 {name:'Collision course',short:'Collision course',goal:'Opposing waves collide. Use the space they leave.',type:'pair'},
 {name:'Electrical storm',short:'Electrical storm',goal:'Watch the timing. Keep your next escape route open.',type:'cross'},
 {name:'Find the focus',short:'Find the focus',goal:'Cut the emitter cores. Each restores one health point and earns 250.',type:'hunt'},
 {name:'Restore the rhythm',short:'Rhythm rescue',goal:'Disable all three emitters. Surviving alone will not finish the run.',type:'boss'}
];
export const DIFFICULTIES={easy:{name:'Easy',interval:10},medium:{name:'Medium',interval:30},hard:{name:'Hard',interval:60}};
export const CUTTERS={
 standard:{id:'standard',name:'Pulse cutter',range:18,radius:2.6,period:.32,description:'A balanced beam for opening a route.'},
 lance:{id:'lance',name:'Lance',range:30,radius:1.6,period:.40,description:'Reach further. Keep your aim precise.'},
 fan:{id:'fan',name:'Fan',range:13,radius:4,period:.42,description:'A broader opening, at closer range.'},
 double:{id:'double',name:'Double pulse',range:18,radius:2.2,period:.14,description:'Two quick cuts, then a longer recovery.'}
};
export function upgradeChoices(tier){if(tier>=3)return[
 {id:'cycle',name:'Overcharge',tag:'FASTER',description:'Reduce recovery by 12%. Restore one health point.',tradeoff:'Stacks with earlier power-ups · minimum 0.09s cycle'},
 {id:'reach',name:'Long lens',tag:'FURTHER',description:'Add 4 reach. Restore one health point.',tradeoff:'Stacks with earlier power-ups · maximum 50 reach'},
 {id:'aperture',name:'Broad lens',tag:'WIDER',description:'Add 1 beam width. Restore one health point.',tradeoff:'Stacks with earlier power-ups · maximum 12 width'}
 ];return tier===1?[
 {id:'lance',name:'Lance',tag:'REACH',description:'Cut a longer, narrower passage.',tradeoff:'30 reach · narrow beam · 0.40s cycle'},
 {id:'fan',name:'Fan',tag:'SPACE',description:'Open a wider gap at close range.',tradeoff:'13 reach · broad beam · 0.42s cycle'},
 {id:'double',name:'Double pulse',tag:'TIMING',description:'Make two cuts in quick succession.',tradeoff:'0.14s between pulses · 0.58s recovery'}
 ]:[
 {id:'cycle',name:'Quick cycle',tag:'PACE',description:'Reduce your cutter’s recovery time by 20%.',tradeoff:'Keep your current beam shape.'},
 {id:'reach',name:'Extended reach',tag:'PRECISION',description:'Add 7 units of reach to your cutter.',tradeoff:'The beam becomes 15% narrower.'},
 {id:'aperture',name:'Wide aperture',tag:'CLEARANCE',description:'Widen your beam by 2 units.',tradeoff:'Lose 2 units of forward reach.'}
 ];}
function random(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t^=t+Math.imul(t^t>>>7,61|t);return((t^t>>>14)>>>0)/4294967296;};}
export function inBeam(px,py,shot,extra=0){const x=((px-shot.x+W*1.5)%W)-W/2,y=py-shot.y;const d=Math.max(0,Math.min(shot.range,x*shot.dx+y*shot.dy));return(x-d*shot.dx)**2+(y-d*shot.dy)**2<=(shot.radius+extra)**2;}
export class Run {
 constructor(seed=17,practice=false,difficulty='hard'){this.difficulty=DIFFICULTIES[difficulty]?difficulty:'hard';this.powerupInterval=DIFFICULTIES[this.difficulty].interval;this.nextPowerup=this.powerupInterval;this.boosts={cycle:0,reach:0,aperture:0};this.field=new Field('surge');this.field.surface=true;this.seed=seed;this.practice=practice;this.rng=random(seed);this.pickupRng=random(seed^0x725ac31);this.pickups=[];this.nextPickup=6;this.repairs=0;this.x=W/2;this.y=H*.62;this.aimX=0;this.aimY=-1;this.time=0;this.hp=3;this.invulnerable=2;this.cooldown=0;this.stage=1;this.nextWave=2;this.warnings=[];this.shots=[];this.impacts=[];this.emitters=[];this.hits=0;this.cuts=0;this.kills=0;this.bossKills=0;this.dead=false;this.won=false;this.damageFlash=0;this.upgradePending=0;this.upgradeTier=0;this.cutter='standard';this.mod=null;this.pulse=0;this.bannerTime=4;this.notice='First pulse';this.events=[];this.emitterSerial=0;}
 get encounter(){return ENCOUNTERS[this.stage-1];}
 get weapon(){const w={...CUTTERS[this.cutter]};if(this.mod==='cycle')w.period*=.8;if(this.mod==='reach'){w.range+=7;w.radius*=.85;}if(this.mod==='aperture'){w.radius+=1;w.range-=2;}w.period=Math.max(.09,w.period*.88**this.boosts.cycle);w.range=Math.min(50,w.range+4*this.boosts.reach);w.radius=Math.min(6,w.radius+.5*this.boosts.aperture);w.offset=w.radius+1.5;return w;}
 get score(){return Math.floor(Math.min(150,this.time)*10)+this.kills*250+(this.won?Math.max(0,3000-Math.floor(Math.max(0,this.time-150)*20))+this.hp*200:0);}
 get phaseTime(){return this.time-(this.stage-1)*30;}
 get roundRemaining(){return this.stage===6?null:Math.min(30,Math.max(0,30-this.phaseTime));}
 get quiet(){return this.stage<5&&this.phaseTime>=26;}
 chooseUpgrade(id){if(!this.upgradePending)return false;const tier=this.upgradePending;if(!upgradeChoices(tier).some(x=>x.id===id))return false;if(tier===1)this.cutter=id;else if(tier===2)this.mod=id;else{this.boosts[id]++;this.hp=Math.min(3,this.hp+1);}this.upgradeTier=tier;this.upgradePending=0;this.cooldown=0;this.pulse=0;this.invulnerable=Math.max(this.invulnerable,2);this.bannerTime=3;this.notice=tier===1?`${this.weapon.name} online`:tier===2?'Cutter refined':'Power-up online · health restored';this.events.push('upgrade');return true;}
 enterStage(stage){this.pickups=[];this.nextPickup=this.time+6;this.field.reset();this.field.a.fill(0);this.field.b.fill(0);this.shots=[];this.impacts=[];this.damageFlash=0;this.stage=stage;this.hp=Math.min(3,this.hp+1);this.invulnerable=2;this.warnings=[];this.emitters=[];this.nextWave=this.time+2;this.bannerTime=4;this.notice=this.encounter.name;this.events.push('stage');
  if(stage===5){this.addEmitter(30,30,'A',false,1.2);this.addEmitter(130,72,'B',false,3.8);}
  if(stage===6){this.addEmitter(32,28,'A',true,2);this.addEmitter(128,28,'B',true,3.5);this.addEmitter(80,79,'C',true,5);this.bannerTime=5;}
 }
 spawnPickup(){if(this.pickups.length>=2)return false;const rand=this.pickupRng;for(let attempt=0;attempt<48;attempt++){const angle=rand()*Math.PI*2,distance=18+rand()*17,x=((this.x+Math.cos(angle)*distance)%W+W)%W,y=this.y+Math.sin(angle)*distance;if(y<12||y>H-12)continue;const dist=(a,b)=>Math.hypot(((a-x+W*1.5)%W)-W/2,b-y);if(this.field.danger(x,y)||this.field.danger(x+2,y)||this.field.danger(x-2,y)||this.field.danger(x,y+2)||this.field.danger(x,y-2))continue;if(this.emitters.some(e=>!e.dead&&dist(e.x,e.y)<9)||this.pickups.some(p=>dist(p.x,p.y)<12)||this.warnings.some(w=>dist(w.x,w.y)<10))continue;this.pickups.push({x,y,born:this.time,expires:this.time+16});this.events.push('supply');return true;}return false;}
 updatePickups(){this.pickups=this.pickups.filter(p=>p.expires>this.time);if(this.time>=this.nextPickup){this.spawnPickup();this.nextPickup=this.time+14;}if(this.dead||this.won)return;this.pickups=this.pickups.filter(p=>{const dx=((p.x-this.x+W*1.5)%W)-W/2;if(this.hp>=3||Math.hypot(dx,p.y-this.y)>2.7)return true;this.hp=Math.min(3,this.hp+1);this.repairs++;this.impacts.push({x:p.x,y:p.y,life:.9,repair:true});this.notice='health restored · +1';this.bannerTime=1.6;this.events.push('repair');return false;});}
 addEmitter(x,y,label,boss,delay){this.emitters.push({id:++this.emitterSerial,x,y,label,boss,hp:boss?10:5,maxHp:boss?10:5,next:this.time+delay,flash:0,dead:false});}
 warn(x,y,{delay=1.6,r=3.2,line=null,source=null}={}){this.warnings.push({x,y,at:this.time+delay,r,line,source});}
 makeWave(){const r=this.rng,t=this.encounter.type,p=.18+r()*.64;
  if(t==='rings'){const side=Math.floor(r()*4);this.warn(side===0?4:side===1?W-5:p*W,side===2?4:side===3?H-5:p*H);this.nextWave=this.time+8;}
  if(t==='wall'){const side=Math.floor(r()*4);if(side<2){const x=side?W-5:4;this.warn(x,H/2,{line:{x1:x,y1:19,x2:x,y2:H-19},r:1.8});}else{const y=side===2?4:H-5;this.warn(W/2,y,{line:{x1:28,y1:y,x2:W-28,y2:y},r:1.8});}this.nextWave=this.time+9;}
  if(t==='pair'){if(r()<.5){this.warn(4,p*H);this.warn(W-5,(1-p)*H,{delay:2.2});}else{this.warn(p*W,4);this.warn((1-p)*W,H-5,{delay:2.2});}this.nextWave=this.time+9;}
  if(t==='cross'){this.warn(4,p*H);this.warn((1-p)*W,4,{delay:2.7});this.warn(W-5,(1-p)*H,{delay:3.8});this.nextWave=this.time+8.5;}
  if(t==='hunt'||t==='boss')this.nextWave=Infinity;
 }
 fire(){const w=this.weapon,shot={x:this.x+this.aimX*w.offset,y:this.y+this.aimY*w.offset,dx:this.aimX,dy:this.aimY,range:w.range,radius:w.radius,life:.13};this.field.clearRay(shot.x,shot.y,shot.dx,shot.dy,shot.range,shot.radius);this.shots.push(shot);this.cuts++;this.events.push('cut');
  if(this.cutter==='double'){this.pulse=1-this.pulse;this.cooldown=(this.pulse?.14:.58)*(this.mod==='cycle'?.8:1)*.88**this.boosts.cycle;this.cooldown=Math.max(.09,this.cooldown);}else this.cooldown=w.period;
  for(const e of this.emitters){if(e.dead||!inBeam(e.x,e.y,shot,1.8))continue;e.hp--;e.flash=.15;this.events.push('core');if(e.hp<=0){e.dead=true;this.kills++;if(e.boss)this.bossKills++;const repair=this.hp<3;this.hp=Math.min(3,this.hp+1);this.notice=`Emitter ${e.label} offline${repair?' · +1 health':''}`;this.bannerTime=2;this.warnings=this.warnings.filter(s=>s.source!==e.id);this.impacts.push({x:e.x,y:e.y,life:.7});this.events.push('destroy');if(e.boss&&this.bossKills===3){this.won=true;this.notice='Field contained';this.events.push('victory');}}}
 }
 update(input={},dt=1/60){if(this.dead||this.won||this.upgradePending)return;this.time+=dt;if(Math.abs(this.time-this.nextPowerup)<1e-8)this.time=this.nextPowerup;const stage=Math.min(6,1+Math.floor((this.time+1e-8)/30));if(stage!==this.stage)this.enterStage(stage);if(this.time+1e-8>=this.nextPowerup){this.nextPowerup+=this.powerupInterval;this.upgradePending=this.upgradeTier+1;return;}
  this.invulnerable=Math.max(0,this.invulnerable-dt);this.cooldown=Math.max(0,this.cooldown-dt);this.damageFlash=Math.max(0,this.damageFlash-dt);this.bannerTime=Math.max(0,this.bannerTime-dt);
  let mx=input.mx||0,my=input.my||0;const m=Math.hypot(mx,my);if(m>1){mx/=m;my/=m;}const speed=input.focus?19:35;this.x=((this.x+mx*speed*dt)%W+W)%W;this.y=Math.max(4,Math.min(H-5,this.y+my*speed*dt));
  const aim=Math.hypot(input.ax||0,input.ay||0);if(aim>.01){this.aimX=input.ax/aim;this.aimY=input.ay/aim;}
  if(input.fire&&this.cooldown<=0){this.fire();if(this.won)return;}
  if(!this.quiet&&this.time>=this.nextWave)this.makeWave();
  for(const e of this.emitters){e.flash=Math.max(0,e.flash-dt);if(!e.dead&&this.time>=e.next){this.warn(e.x,e.y,{r:3.5,source:e.id});e.next=this.time+(e.boss?5.8:7.5);}}
  this.warnings=this.warnings.filter(s=>{if(s.at>this.time)return true;if(s.line)this.field.seedLine(s.line.x1,s.line.y1,s.line.x2,s.line.y2,s.r);else this.field.seed(s.x,s.y,s.r);return false;});
  for(let j=0;j<4;j++)this.field.step();
  let hit=false;for(const[dx,dy]of[[0,0],[.7,0],[-.7,0],[0,.7],[0,-.7]])if(this.field.danger(this.x+dx,this.y+dy))hit=true;
  if(hit&&this.invulnerable<=0){this.hits++;this.hp--;this.damageFlash=.25;this.impacts.push({x:this.x,y:this.y,life:.6});this.invulnerable=1.8;this.field.clearRay(this.x-4,this.y,1,0,8,4);this.events.push('hit');if(this.hp<=0){if(this.practice)this.hp=3;else this.dead=true;}}
  if(!this.dead)this.updatePickups();
  for(const s of this.shots)s.life-=dt;this.shots=this.shots.filter(s=>s.life>0);for(const s of this.impacts)s.life-=dt;this.impacts=this.impacts.filter(s=>s.life>0);if(this.events.length>24)this.events=this.events.slice(-24);
 }
 jumpTo(stage){if(!this.practice||!Number.isInteger(stage)||stage<1||stage>6)return false;this.field.reset();this.time=(stage-1)*30+.001;this.nextPowerup=(Math.floor(this.time/this.powerupInterval)+1)*this.powerupInterval;this.dead=false;this.won=false;this.hp=3;this.bossKills=0;this.upgradeTier=stage>=5?2:stage>=3?1:0;this.upgradePending=0;this.x=W/2;this.y=H*.62;this.enterStage(stage);return true;}
 stats(){let count=0,max=0;for(const n of this.field.u){if(n>.45)count++;if(n>max)max=n;}return{time:this.time,hp:this.hp,repairs:this.repairs,pickups:this.pickups.length,hits:this.hits,cuts:this.cuts,kills:this.kills,bossKills:this.bossKills,score:this.score,coverage:count/(W*H),maximum:max,stage:this.stage,dead:this.dead,won:this.won,x:this.x,y:this.y,cutter:this.cutter,mod:this.mod,upgradePending:this.upgradePending,difficulty:this.difficulty,boosts:{...this.boosts}};}
}
