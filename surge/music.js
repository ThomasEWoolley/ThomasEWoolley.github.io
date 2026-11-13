// Original 84 BPM heartbeat/synth soundtrack; no downloads and no autoplay.
export const HEARTBEAT_BPM=84;
export class HeartbeatMusic{
 constructor({createContext=()=>new (globalThis.AudioContext||globalThis.webkitAudioContext)(),setTimer=(fn,ms)=>setInterval(fn,ms),clearTimer=id=>clearInterval(id)}={}){this.createContext=createContext;this.setTimer=setTimer;this.clearTimer=clearTimer;this.enabled=false;this.playing=false;this.allowed=true;this.volume=.35;this.nodes=new Set();this.timer=null;this.ticket=0;this.beat=0;}
 async setEnabled(value){this.enabled=!!value;const ticket=++this.ticket;if(!this.enabled){this.stop();return;}try{if(!this.ctx){this.ctx=this.createContext();this.master=this.ctx.createGain();this.master.gain.value=0;this.master.connect(this.ctx.destination);}await this.ctx.resume();if(ticket!==this.ticket||!this.enabled)return;if(this.allowed)this.start();}catch(error){if(ticket===this.ticket){this.enabled=false;this.stop();}throw error;}}
 setVolume(value){this.volume=Math.max(0,Math.min(1,Number(value)||0));if(this.ctx&&this.playing){const now=this.ctx.currentTime;this.master.gain.cancelScheduledValues(now);this.master.gain.setTargetAtTime(this.volume*.55,now,.04);}}
 update(state,hidden=false){const allowed=!hidden&&(state==='play'||state==='menu');if(allowed===this.allowed)return;this.allowed=allowed;if(!allowed)this.stop();else if(this.enabled&&this.ctx?.state==='running')this.start();}
 start(){if(this.playing||!this.enabled||!this.allowed||!this.ctx)return;this.playing=true;this.beat=0;this.next=this.ctx.currentTime+.06;const now=this.ctx.currentTime;this.master.gain.cancelScheduledValues(now);this.master.gain.setTargetAtTime(this.volume*.55,now,.07);this.schedule();this.timer=this.setTimer(()=>this.schedule(),70);}
 stop(){if(this.timer!==null){this.clearTimer(this.timer);this.timer=null;}this.playing=false;if(!this.ctx)return;const now=this.ctx.currentTime;this.master.gain.cancelScheduledValues(now);this.master.gain.setTargetAtTime(0,now,.015);for(const node of this.nodes){try{node.stop(now+.06);}catch{}}this.nodes.clear();}
 voice(at,frequency,duration,level,type='sine',endFrequency=null){const osc=this.ctx.createOscillator(),gain=this.ctx.createGain();osc.type=type;osc.frequency.setValueAtTime(frequency,at);if(endFrequency)osc.frequency.exponentialRampToValueAtTime(endFrequency,at+duration*.8);gain.gain.setValueAtTime(.0001,at);gain.gain.exponentialRampToValueAtTime(level,at+Math.min(.018,duration*.1));gain.gain.exponentialRampToValueAtTime(.0001,at+duration);osc.connect(gain);gain.connect(this.master);this.nodes.add(osc);osc.onended=()=>{this.nodes.delete(osc);osc.disconnect();gain.disconnect();};osc.start(at);osc.stop(at+duration+.02);}
 schedule(){if(!this.playing)return;const now=this.ctx.currentTime,beatLength=60/HEARTBEAT_BPM;if(this.next<now-.15)this.next=now+.04;while(this.next<now+.22){const at=this.next,index=this.beat;
 // A low double pulse: lub, then dub. Its tempo stays steady during gameplay.
 this.voice(at,92,.16,.5,'sine',46);this.voice(at+.19,116,.13,.29,'sine',62);
 // Four gentle chords, voiced above the pulse.
 const chords=[[220,261.63,329.63],[174.61,220,261.63],[196,246.94,293.66],[164.81,196,246.94]],chord=chords[Math.floor(index/4)%4];
 if(index%4===0)for(const f of chord)this.voice(at,f,beatLength*4.1,.028,'sine');
 const melody=[440,0,523.25,0,659.25,587.33,523.25,0,392,0,493.88,0,587.33,493.88,392,0],note=melody[index%melody.length];if(note)this.voice(at+beatLength*.5,note,beatLength*.8,.035,'sine');
 this.beat++;this.next+=beatLength;}}
 get status(){return {enabled:this.enabled,playing:this.playing,volume:this.volume,bpm:HEARTBEAT_BPM};}
}
