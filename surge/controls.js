// WASD always moves. Arrows only aim/fire in the selected arrows scheme.
export function keyboardControls(keys,taps=new Set(),aimMode='arrows'){
 const held=k=>keys.has(k)||taps.has(k),right=held('arrowright'),left=held('arrowleft'),down=held('arrowdown'),up=held('arrowup');
 const ax=Number(right)-Number(left),ay=Number(down)-Number(up),shoot=aimMode==='arrows';
 return {mx:Number(held('d'))-Number(held('a')),my:Number(held('s'))-Number(held('w')),ax,ay,aiming:shoot&&(ax!==0||ay!==0),fire:shoot&&(ax!==0||ay!==0)};
}
