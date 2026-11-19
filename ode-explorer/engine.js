/* Browser and Node numerical core. No eval or generated JavaScript. */
(function(root){
'use strict';
const functions={sin:Math.sin,cos:Math.cos,tan:Math.tan,asin:Math.asin,acos:Math.acos,atan:Math.atan,sinh:Math.sinh,cosh:Math.cosh,tanh:Math.tanh,exp:Math.exp,log:Math.log,ln:Math.log,log10:Math.log10,sqrt:Math.sqrt,abs:Math.abs,sign:Math.sign,floor:Math.floor,ceil:Math.ceil,min:Math.min,max:Math.max,pow:Math.pow,atan2:Math.atan2};
function tokenize(source){
 if(!source.trim()||source.length>1000) throw Error('Enter an expression of at most 1,000 characters.');
 source=source.replace(/[−–]/g,'-').replace(/·|×/g,'*').replace(/\.([*/^])/g,'$1').replace(/\*\*/g,'^');
 const tokens=[];let pos=0;
 while(pos<source.length){const rest=source.slice(pos);let m;
 if((m=/^\s+/.exec(rest))){pos+=m[0].length;continue;}
 if((m=/^(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/.exec(rest))){tokens.push({type:'number',value:Number(m[0])});pos+=m[0].length;continue;}
 if((m=/^[a-zA-Z_][a-zA-Z_0-9]*/.exec(rest))){tokens.push({type:'id',value:m[0]});pos+=m[0].length;continue;}
 if('+-*/^(),'.includes(rest[0])){tokens.push({type:rest[0]});pos++;continue;}
 throw Error('Unsupported character: '+rest[0]);}
 return tokens;
}
function compile(source,variables=['u','v']){
 const tokens=tokenize(source); tokens.push({type:'end'});let i=0,depth=0;
 const at=()=>tokens[i];const take=()=>tokens[i++];
 function expr(min=0){if(++depth>80)throw Error('Expression is too deeply nested.');let t=take(),node;
 if(t.type==='number')node=()=>t.value;
 else if(t.type==='+'||t.type==='-'){const a=expr(25);node=t.type==='-'?s=>-a(s):a;}
 else if(t.type==='('){node=expr();if(take().type!==')')throw Error('Missing closing bracket.');}
 else if(t.type==='id'){
 if(Object.hasOwn(functions,t.value)){
 if(take().type!=='(')throw Error('Use '+t.value+'(...).');const args=[expr()];while(at().type===','){take();args.push(expr());}if(take().type!==')')throw Error('Missing closing bracket.');
 const arity=['min','max','pow','atan2'].includes(t.value)?2:1;if(args.length!==arity)throw Error(t.value+' needs '+arity+' argument(s).');node=s=>functions[t.value](...args.map(a=>a(s)));
 }else if(t.value==='pi')node=()=>Math.PI;else if(t.value==='e')node=()=>Math.E;
 else if(variables.includes(t.value))node=s=>s[t.value];else throw Error('Unknown name “'+t.value+'”. Define it in Parameters, or use '+variables.join(', ')+'.');
 }else throw Error('Expected a number, variable or bracket.');
 while(true){const op=at().type;let prec=({'+':10,'-':10,'*':20,'/':20,'^':30})[op],implicit=false;
 if(prec===undefined&&['number','id','('].includes(op)){prec=20;implicit=true;}
 if(prec===undefined||prec<min)break;if(!implicit)take();const a=node,b=expr(prec+(op==='^'?0:1));
 node=(implicit||op==='*')?s=>a(s)*b(s):op==='+'?s=>a(s)+b(s):op==='-'?s=>a(s)-b(s):op==='/'?s=>a(s)/b(s):s=>a(s)**b(s);
 }depth--;return node;}
 const fn=expr();if(at().type!=='end')throw Error('Unexpected token. Check brackets and operators.');return fn;
}
function parameters(text){const result=Object.create(null);for(const row of text.split(/[;\n]/).filter(x=>x.trim())){
 const m=/^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*(.+?)\s*$/.exec(row);if(!m)throw Error('Write parameters as r = 1; K = 10.');const name=m[1];if(['u','v','t','pi','e'].includes(name)||Object.hasOwn(functions,name)||Object.hasOwn(result,name))throw Error('Reserved or repeated parameter: '+name);
 const val=compile(m[2],Object.keys(result))(result);if(!Number.isFinite(val))throw Error('Parameter '+name+' must be finite.');result[name]=val;}return result;}
// Parameter discovery uses the expression lexer, so scientific notation is not a name.
function parameterNames(sources){const names=new Set();for(const source of sources){if(!source.trim())continue;for(const token of tokenize(source))if(token.type==='id'&&!['u','v','pi','e'].includes(token.value)&&!Object.hasOwn(functions,token.value))names.add(token.value);}return [...names];}
function parameterSpec(raw,name='Parameter'){
 const numeric=(v,label)=>{if(v===undefined||String(v).trim()===''||!Number.isFinite(Number(v)))throw Error(name+': enter a finite '+label+'.');return Number(v);};
 const baseline=numeric(raw.baseline,'baseline');const hasMin=raw.min!==undefined&&String(raw.min).trim()!=='',hasMax=raw.max!==undefined&&String(raw.max).trim()!=='';
 if(hasMin!==hasMax)throw Error(name+': supply both limits, or leave both blank to keep it fixed.');
 if(!hasMin)return {baseline,min:baseline,max:baseline,value:baseline,fixed:true};
 const min=numeric(raw.min,'minimum'),max=numeric(raw.max,'maximum');if(min>max)throw Error(name+': the minimum must not exceed the maximum.');if(baseline<min||baseline>max)throw Error(name+': the baseline must lie between the minimum and maximum.');
 if(!Number.isFinite(max-min))throw Error(name+': the parameter range is too large.');
 const value=raw.value!==undefined&&Number.isFinite(Number(raw.value))&&Number(raw.value)>=min&&Number(raw.value)<=max?Number(raw.value):baseline;
 return {baseline,min,max,value,fixed:min===max};
}
function eigenvalues2x2(trace,determinant){const disc=trace*trace-4*determinant;if(disc<0)return [{re:trace/2,im:Math.sqrt(-disc)/2},{re:trace/2,im:-Math.sqrt(-disc)/2}];const first=(trace+(trace>=0?1:-1)*Math.sqrt(disc))/2,second=first===0?0:determinant/first;return [{re:first,im:0},{re:second,im:0}].sort((a,b)=>b.re-a.re);}
function system(f,g,dimension,params){const vars=dimension===1?['u',...Object.keys(params)]:['u','v',...Object.keys(params)];const ff=compile(f,vars),gg=dimension===2?compile(g,vars):null;return y=>{const s={...params,u:y[0],v:y[1]};return gg?[ff(s),gg(s)]:[ff(s)];};}
// Dormand–Prince 5(4), with weighted local error and rejected-step control.
const A=[[],[1/5],[3/40,9/40],[44/45,-56/15,32/9],[19372/6561,-25360/2187,64448/6561,-212/729],[9017/3168,-355/33,46732/5247,49/176,-5103/18656],[35/384,0,500/1113,125/192,-2187/6784,11/84]];
const B=[35/384,0,500/1113,125/192,-2187/6784,11/84,0], E=[35/384-5179/57600,0,500/1113-7571/16695,125/192-393/640,-2187/6784+92097/339200,11/84-187/2100,-1/40];
function integrate(fn,y0,options={}){
 const {t0=0,t1=20,maxStep=.1,rtol=1e-6,atol=1e-9,maxSteps=60000,method='rk45',magnitudeLimit=1e7}=options;
 if(![t0,t1,maxStep,rtol,atol,...y0].every(Number.isFinite)||t0===t1||maxStep<=0||rtol<=0||atol<=0)throw Error('Invalid initial condition or solver settings.');
 const direction=Math.sign(t1-t0),points=[[t0,...y0]];let t=t0,y=y0.slice(),h=direction*Math.min(maxStep,Math.abs(t1-t0)/(method==='rk4'?1:100)),attempts=0,rejected=0,reason='Completed';
 const finite=a=>a.every(Number.isFinite);
 if(!finite(fn(y)))return {points,reason:'Equation undefined at the initial condition',rejected,attempts};
 while(direction*(t1-t)>Math.max(1e-14,Math.abs(t1)*1e-14)){
 if(++attempts>maxSteps){reason='Step limit reached. Shorten the interval or use a smaller maximum step for a stiff system.';break;}
 h=direction*Math.min(Math.abs(h),Math.abs(t1-t),maxStep);if(t+h===t||Math.abs(h)<1e-14*Math.max(1,Math.abs(t))){reason='Step size too small near a singularity or a stiff region';break;}
 let next,err=0;
 if(method==='rk4'){
 const k1=fn(y),k2=fn(y.map((v,j)=>v+h*k1[j]/2)),k3=fn(y.map((v,j)=>v+h*k2[j]/2)),k4=fn(y.map((v,j)=>v+h*k3[j]));next=y.map((v,j)=>v+h*(k1[j]+2*k2[j]+2*k3[j]+k4[j])/6);
 }else{
 const k=[];for(let stage=0;stage<7;stage++)k.push(fn(y.map((v,j)=>v+h*A[stage].reduce((sum,a,l)=>sum+a*k[l][j],0))));
 next=y.map((v,j)=>v+h*B.reduce((sum,b,l)=>sum+b*k[l][j],0));
 err=Math.max(...y.map((v,j)=>Math.abs(h*E.reduce((sum,e,l)=>sum+e*k[l][j],0))/(atol+rtol*Math.max(Math.abs(v),Math.abs(next[j])))));
 }
 if(!finite(next)||!Number.isFinite(err)){
 if(method==='rk45'&&Math.abs(h)>1e-12){h*=.2;rejected++;continue;}reason='Equation became undefined or non-finite';break;}
 if(method==='rk45'&&err>1){h*=Math.max(.1,.9*err**(-.2));rejected++;continue;}
 if(next.some(v=>Math.abs(v)>magnitudeLimit)){reason='Stopped at the magnitude limit (possible blow-up)';break;}
 t+=h;y=next;points.push([t,...y]);if(method==='rk45')h*=err===0?5:Math.max(.2,Math.min(5,.9*err**(-.2)));else h=direction*maxStep;
 }
 return {points,reason,rejected,attempts};
}
function roots1D(fn,min,max){const N=1200,x=Array.from({length:N+1},(_,i)=>min+(max-min)*i/N),f=x.map(u=>fn([u])[0]),roots=[],tol=(max-min)*1e-6;
 function add(u){if(Number.isFinite(u)&&Math.abs(fn([u])[0])<1e-7&&u>=min-tol&&u<=max+tol&&!roots.some(r=>Math.abs(r-u)<tol*5))roots.push(u);}
 for(let i=0;i<=N;i++){
 if(!Number.isFinite(f[i]))continue;if(Math.abs(f[i])<1e-10)add(x[i]);
 if(i<N&&f[i]*f[i+1]<0){let a=x[i],b=x[i+1],fa=f[i];for(let k=0;k<45;k++){let m=(a+b)/2,fm=fn([m])[0];if(fa*fm<=0)b=m;else{a=m;fa=fm;}}add((a+b)/2);}
 // Newton seeds at local minima of |f| also detect even-multiplicity roots.
 if(i>0&&i<N&&Math.abs(f[i])<=Math.abs(f[i-1])&&Math.abs(f[i])<=Math.abs(f[i+1])){let u=x[i];for(let k=0;k<60;k++){let z=fn([u])[0],d=(max-min)*1e-6,der=(fn([u+d])[0]-fn([u-d])[0])/(2*d);if(!Number.isFinite(der)||Math.abs(der)<1e-14)break;const step=z/der;u-=step;if(Math.abs(step)<1e-12)break;}add(u);}}
 return roots.sort((a,b)=>a-b).map(u=>{const h=Math.max(1e-5,(max-min)*1e-4),left=fn([u-h])[0],right=fn([u+h])[0];const dh=Math.cbrt(Number.EPSILON)*Math.max(1,Math.abs(u)),derivative=(fn([u+dh])[0]-fn([u-dh])[0])/(2*dh);return {u,v:0,derivative,eigenvalues:[{re:derivative,im:0}],label:left>0&&right<0?'Stable':left<0&&right>0?'Unstable':left*right>0?'Semistable':'Non-hyperbolic'};});}
function equilibria(fn,bounds){const [xmin,xmax,ymin,ymax]=bounds,dx=xmax-xmin,dy=ymax-ymin,res=[];
 // Work in dimensionless window coordinates so differently scaled axes remain usable.
 const F=(x,y)=>{const f=fn([xmin+x*dx,ymin+y*dy]);return [f[0]/dx,f[1]/dy];};
 for(let i=0;i<=14;i++)for(let j=0;j<=14;j++){
 let x=i/14,y=j/14;
 for(let k=0;k<45;k++){const f=F(x,y),h=1e-5,fx=F(x+h,y),bx=F(x-h,y),fy=F(x,y+h),by=F(x,y-h),a=(fx[0]-bx[0])/(2*h),b=(fy[0]-by[0])/(2*h),c=(fx[1]-bx[1])/(2*h),d=(fy[1]-by[1])/(2*h),det=a*d-b*c;
 if(![...f,a,b,c,d,det].every(Number.isFinite)||Math.abs(det)<1e-14)break;
 if(Math.hypot(...f)<1e-10)break;
 let sx=(d*f[0]-b*f[1])/det,sy=(-c*f[0]+a*f[1])/det,lim=Math.max(1,Math.hypot(sx,sy)/.5);x-=sx/lim;y-=sy/lim;if(Math.abs(x)>10||Math.abs(y)>10)break;}
 if(x< -1e-7||x>1+1e-7||y< -1e-7||y>1+1e-7||!Number.isFinite(x+y)||Math.hypot(...F(x,y))>1e-8||res.some(r=>Math.hypot((r.u-xmin)/dx-x,(r.v-ymin)/dy-y)<1e-4))continue;
 const u=xmin+x*dx,v=ymin+y*dy,h=1e-5,fx=F(x+h,y),bx=F(x-h,y),fy=F(x,y+h),by=F(x,y-h),a=(fx[0]-bx[0])/(2*h),b=(fy[0]-by[0])/(2*h),c=(fx[1]-bx[1])/(2*h),d=(fy[1]-by[1])/(2*h),tr=a+d,det=a*d-b*c,disc=tr*tr-4*det,eps=1e-7*Math.max(1,Math.abs(a),Math.abs(b),Math.abs(c),Math.abs(d));
 let label=det< -eps?'Saddle':Math.abs(det)<=eps?'Non-hyperbolic':Math.abs(tr)<=eps&&disc<0?'Centre (linearisation)':disc<0?(tr<0?'Stable spiral':'Unstable spiral'):(tr<0?'Stable node':'Unstable node');
 res.push({u,v,label,tr,det,eigenvalues:eigenvalues2x2(tr,det),jacobian:[[a,b*dx/dy],[c*dy/dx,d]]});}
 return res.sort((a,b)=>a.u-b.u||a.v-b.v);
}
const api={compile,parameters,parameterNames,parameterSpec,eigenvalues2x2,system,integrate,roots1D,equilibria};if(typeof module!=='undefined')module.exports=api;else root.ODE=api;
})(typeof window==='undefined'?globalThis:window);
