importScripts('engine.js');
self.onmessage=({data})=>{try{const fn=ODE.system(data.config.f,data.config.g,data.config.dim,data.config.paramValues);const results=data.initials.map(ic=>ODE.integrate(fn,ic,data.config.options));self.postMessage({id:data.id,results});}catch(e){self.postMessage({id:data.id,error:e.message});}};
