// Neith live: quiet -> negative. Instead of fading through flat grey, the inversion spreads in soft organic patches
// (a slowly drifting noise field is the threshold map), so half-way the picture is part negative, part positive.
uniform vec4 uQ;   // quiet amount 0..1 (x), seconds (y), -, -
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
float fbm(vec2 p){ float s=0.0,a=0.5; for(int i=0;i<4;i++){ s+=a*vnoise(p); p=p*2.03+7.1; a*=0.5; } return s/0.9375; }
void main(){
  vec2 uv=vUV.st;
  vec2 R=uTDOutputInfo.res.zw;
  vec3 c=texture(sTD2DInputs[0],uv).rgb;
  float q=clamp(uQ.x,0.0,1.0);
  float n=fbm(vec2(uv.x*R.x/R.y,uv.y)*3.0+vec2(0.0,uQ.y*0.03));
  float m=smoothstep(n-0.12,n+0.12,q*1.24-0.12);          // q=0 -> none, q=1 -> all
  fragColor=TDOutputSwizzle(vec4(mix(c,1.0-c,m),1.0));
}
