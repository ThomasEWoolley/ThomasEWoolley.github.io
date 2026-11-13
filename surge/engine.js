// Patternfall: deterministic CPU reference solver shared by the game and tests.
export const W=160,H=104;
export class Field {
  constructor(kind='surge',w=W,h=H){this.kind=kind;this.w=w;this.h=h;this.u=new Float32Array(w*h);this.v=new Float32Array(w*h);this.a=new Float32Array(w*h);this.b=new Float32Array(w*h);this.reset();}
  reset(){this.u.fill(this.kind==='spots'?1:0);this.v.fill(0);}
  seed(cx,cy,r=4){if(this.surface){for(let y=Math.max(0,Math.floor(cy-r));y<Math.min(this.h,cy+r+1);y++)for(let xx=Math.floor(cx-r);xx<cx+r+1;xx++){if((xx-cx)**2+(y-cy)**2>r*r)continue;const x=((xx%this.w)+this.w)%this.w,i=y*this.w+x;this.u[i]=1;this.v[i]=0;}return;}const {w,h,u,v}=this;for(let y=Math.max(1,Math.floor(cy-r));y<Math.min(h-1,cy+r+1);y++)for(let x=Math.max(1,Math.floor(cx-r));x<Math.min(w-1,cx+r+1);x++){if(this.kind!=='spots'&&(x-cx)**2+(y-cy)**2>r*r)continue;const i=y*w+x;if(this.kind==='spots'){u[i]=.5;v[i]=.25*(1+.02*Math.sin(x*12.9898+y*78.233));}else{u[i]=1;v[i]=0;}}}
  step(){if(this.surface)return this.surfaceStep();const {w,h,u,v,a,b}=this;const spots=this.kind==='spots';for(let y=1;y<h-1;y++){for(let x=1;x<w-1;x++){const i=y*w+x,U=u[i],V=v[i],lap=u[i-1]+u[i+1]+u[i-w]+u[i+w]-4*U;
    if(spots){const lv=v[i-1]+v[i+1]+v[i-w]+v[i+w]-4*V;const r=U*V*V;
      // Gray–Scott with a fixed downward carrier current, first-order upwind.
      a[i]=U+.16*lap-r+.02*(1-U)-.045*(U-u[i-w]);
      b[i]=V+.08*lv+r-(.02+.059)*V-.045*(V-v[i-w]);
    }else{ // Barkley excitable medium, explicit Euler, dx=1 and dt=.025.
      a[i]=U+.025*(lap+U*(1-U)*(U-(V+.025)/.75)/.04);
      b[i]=V+.025*(U-V);
    }
    // Discard negligible tails to avoid subnormal arithmetic in empty regions.
    if(b[i]<1e-12)b[i]=0;if(a[i]<1e-12)a[i]=0;
  }}
    // Absorbing edge strips prevent waves wrapping into the arena invisibly.
    const bg=spots?1:0;for(let x=0;x<w;x++){a[x]=a[(h-1)*w+x]=bg;b[x]=b[(h-1)*w+x]=0;}for(let y=0;y<h;y++){a[y*w]=a[y*w+w-1]=bg;b[y*w]=b[y*w+w-1]=0;}
    this.u=a;this.v=b;this.a=u;this.b=v;
  }
  surfaceStep(){const {w,h,u,v,a,b}=this;for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=y*w+x,U=u[i],V=v[i],lap=u[y*w+(x+w-1)%w]+u[y*w+(x+1)%w]+u[Math.max(0,y-1)*w+x]+u[Math.min(h-1,y+1)*w+x]-4*U;a[i]=Math.max(0,U+.025*(lap+U*(1-U)*(U-(V+.025)/.75)/.04));b[i]=Math.max(0,V+.025*(U-V));}this.u=a;this.v=b;this.a=u;this.b=v;}
  seedLine(x1,y1,x2,y2,r=2){const steps=Math.ceil(Math.hypot(x2-x1,y2-y1));for(let i=0;i<=steps;i++){const t=steps?i/steps:0;this.seed(x1+(x2-x1)*t,y1+(y2-y1)*t,r);}}
  value(x,y){if(this.surface)x=((x%this.w)+this.w)%this.w;const i=Math.max(0,Math.min(this.h-1,Math.floor(y)))*this.w+Math.max(0,Math.min(this.w-1,Math.floor(x)));return this.kind==='spots'?this.v[i]:this.u[i];}
  danger(x,y){return this.value(x,y)>(this.kind==='spots'?.14:.45);}
  clearRay(x,y,dx,dy,range=22,radius=3.2){const len=Math.hypot(dx,dy)||1;dx/=len;dy/=len;let removed=0;const {w,h,u,v}=this;const ex=x+dx*range,ey=y+dy*range;
    for(let yy=Math.max(1,Math.floor(Math.min(y,ey)-radius));yy<Math.min(h-1,Math.ceil(Math.max(y,ey)+radius));yy++)for(let xx=(this.surface?Math.floor(Math.min(x,ex)-radius):Math.max(1,Math.floor(Math.min(x,ex)-radius)));xx<(this.surface?Math.ceil(Math.max(x,ex)+radius):Math.min(w-1,Math.ceil(Math.max(x,ex)+radius)));xx++){
      const along=Math.max(0,Math.min(range,(xx-x)*dx+(yy-y)*dy));if((xx-x-along*dx)**2+(yy-y-along*dy)**2>radius*radius)continue;
      const i=yy*w+((xx%w)+w)%w;removed+=this.kind==='spots'?v[i]:u[i];
      if(this.kind==='spots'){u[i]=1;v[i]=0;}else{u[i]=0;v[i]=Math.max(v[i],.9);/* A local inhibitor pulse gives the cut a finite refractory lifetime. */}
    }return removed;
  }
}
function random(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t^=t+Math.imul(t^t>>>7,61|t);return((t^t>>>14)>>>0)/4294967296;};}
export class Game {
  constructor(kind='surge',seed=17,practice=false){this.field=new Field(kind);this.kind=kind;this.seed=seed;this.practice=practice;this.rng=random(seed);this.x=W/2;this.y=H*.62;this.aimX=0;this.aimY=-1;this.time=0;this.hp=3;this.invulnerable=2;this.cooldown=0;this.nextWave=1;this.warnings=[];this.shots=[];this.impacts=[];this.hits=0;this.cuts=0;this.extracted=0;this.dead=false;this.stage=1;this.damageFlash=0;}
  makeWarning(){const r=this.rng;const count=this.kind==='spots'?Math.min(6,3+Math.floor(this.time/25)):Math.min(4,1+Math.floor(this.time/22));for(let j=0;j<count;j++){
    let x,y;if(this.kind==='spots'){x=10+(W-20)*(j+.25+r()*.5)/count;y=7;}else{const side=Math.floor(r()*4);const p=.16+r()*.68;x=side===0?4:side===1?W-5:p*W;y=side===2?4:side===3?H-5:p*H;}
    this.warnings.push({x,y,at:this.time+1.5,r:this.kind==='spots'?5.2:3.2});
  }this.nextWave=this.time+Math.max(2.8,5.5-this.time*.018);}
  update(input={},dt=1/60){if(this.dead)return;this.time+=dt;this.stage=1+Math.floor(this.time/22);this.invulnerable=Math.max(0,this.invulnerable-dt);this.cooldown=Math.max(0,this.cooldown-dt);this.damageFlash=Math.max(0,this.damageFlash-dt);
    let mx=input.mx||0,my=input.my||0;const m=Math.hypot(mx,my);if(m>1){mx/=m;my/=m;}const speed=input.focus?19:35;
    this.x=Math.max(4,Math.min(W-5,this.x+mx*speed*dt));this.y=Math.max(4,Math.min(H-5,this.y+my*speed*dt));
    if(Math.hypot(input.ax||0,input.ay||0)>.01){const q=Math.hypot(input.ax,input.ay);this.aimX=input.ax/q;this.aimY=input.ay/q;}
    if(input.fire&&this.cooldown<=0){const removed=this.field.clearRay(this.x+this.aimX*4,this.y+this.aimY*4,this.aimX,this.aimY,18,2.6);this.extracted+=removed;this.cuts++;this.shots.push({x:this.x,y:this.y,dx:this.aimX,dy:this.aimY,life:.13});this.cooldown=.32;}
    if(this.time>=this.nextWave)this.makeWarning();
    this.warnings=this.warnings.filter(s=>{if(s.at>this.time)return true;this.field.seed(s.x,s.y,s.r);return false;});
    const substeps=this.kind==='spots'?6:4;for(let j=0;j<substeps;j++)this.field.step();
    // The same threshold used by the renderer defines the lethal body.
    let hit=false;for(const [dx,dy]of [[0,0],[.7,0],[-.7,0],[0,.7],[0,-.7]])if(this.field.danger(this.x+dx,this.y+dy))hit=true;
    if(hit&&this.invulnerable<=0){this.hits++;this.hp--;this.damageFlash=.25;this.impacts.push({x:this.x,y:this.y,life:.6});this.invulnerable=1.8;this.field.clearRay(this.x-4,this.y,1,0,8,4);if(this.hp<=0){if(this.practice)this.hp=3;else this.dead=true;}}
    for(const s of this.shots)s.life-=dt;this.shots=this.shots.filter(s=>s.life>0);for(const s of this.impacts)s.life-=dt;this.impacts=this.impacts.filter(s=>s.life>0);
  }
  stats(){let count=0,max=0;for(let i=0;i<this.field.u.length;i++){const n=this.kind==='spots'?this.field.v[i]:this.field.u[i];if(n>(this.kind==='spots'?.14:.45))count++;if(n>max)max=n;}return{time:this.time,hp:this.hp,hits:this.hits,cuts:this.cuts,coverage:count/(W*H),maximum:max,stage:this.stage,dead:this.dead,x:this.x,y:this.y};}
}
