import { TIMELINE } from '../data/constants.js';

export const tToSec = (t) => { const [h,m,s] = t.split(":").map(Number); return h*3600+m*60+s; };
export const TIMES = TIMELINE.map(d => tToSec(d.t));
export const T_MIN = Math.min(...TIMES);
export const T_MAX = Math.max(...TIMES);
export const T_SPAN = T_MAX - T_MIN;
export const BURST_START = tToSec("14:31:02");
export const BURST_END = BURST_START + 90;
export const formatSec = (s) => { const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),ss=Math.floor(s%60); return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(ss).padStart(2,"0")}`; };
