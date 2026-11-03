// Neith live: quiet -> negative, spreading gradually.
// The inversion grows out of large, soft, slowly drifting clouds instead of small hard patches: the threshold map is a
// low-frequency noise field (Invert Spread Size), its edge is very wide (Invert Softness), and part of the inversion is
// a plain even cross-fade, so the picture slides from positive to negative like a tide rather than in patches.
uniform vec4 uQ;   // quiet amount 0..1 (x), seconds (y), Invert Softness 0..1 (z), Invert Spread Size (w)
out vec4 fragColor;
float hpx(vec2 p){
  uvec2 q=uvec2(ivec2(floor(p))+ivec2(1<<20));
  uint h=q.x*1664525u+q.y*1013904223u+0x9e3779b9u;
  h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
  return float(h)*(1.0/4294967295.0);
}
float vnoise(vec2 p){
  vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hpx(i),hpx(i+vec2(1.0,0.0)),f.x), mix(hpx(i+vec2(0.0,1.0)),hpx(i+vec2(1.0,1.0)),f.x), f.y);
}
float fbm(vec2 p){ float s=0.0,a=0.5; for(int i=0;i<3;i++){ s+=a*vnoise(p); p=p*2.03+7.1; a*=0.5; } return s/0.875; }
void main(){
  vec2 uv=vUV.st;
  vec2 R=uTDOutputInfo.res.zw;
  vec3 c=texture(sTD2DInputs[0],uv).rgb;
  float q=clamp(uQ.x,0.0,1.0);
  float soft=clamp(uQ.z,0.0,1.0);
  float scale=max(uQ.w,0.2);
  vec2 p=vec2(uv.x*R.x/R.y,uv.y)*scale;
  float n=fbm(p+vec2(uQ.y*0.008,uQ.y*0.012));                  // large clouds, drifting slowly
  float w=mix(0.12,0.45,soft);                                   // width of the soft edge
  float m=smoothstep(n-w,n+w,q*(1.0+2.0*w)-w);                   // q=0 -> none, q=1 -> all
  m=mix(m,q,0.5*soft);                                           // part of it is an even, gradual cross-fade
  m=m*m*(3.0-2.0*m);
  fragColor=TDOutputSwizzle(vec4(mix(c,1.0-c,m),1.0));
}
