// Visual protection is driven by the same remaining time as damage immunity.
export function protectionVisual(remaining,time,reducedMotion=false){const active=remaining>0;return {active,opacity:active&&!reducedMotion?(Math.floor(time*8)%2===0?1:.16):1};}
