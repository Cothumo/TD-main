// holo_sim_head - the head's own particles (rgba32float, fed back through head_fb). One texel = one particle.
// Each particle lives in cycles (headCycle in holo_common): every cycle it picks a new resting point; points near the
// outline are taken more often, points outside the head are dropped for that cycle. It rests (trembling, drawn by the
// vertex shader) for 'hold', then lifts off and is carried away to the right with the stream.
// state: xy = position (UV), z = cycle number, w = 0 not started / 1 dropped this cycle / 2 in use
// input 0 = the state, input 1 = holo_maps
uniform vec4 uH;   // Particlehold (s), Streamspeed (px/s at 720 high), Turbulence, reset
out vec4 fragColor;
void main() {
	ivec2 px = ivec2(gl_FragCoord.xy);
	ivec2 res = textureSize(sTD2DInputs[0], 0);
	uint id = uint(px.y * res.x + px.x);
	vec4 st = texelFetch(sTD2DInputs[0], px, 0);
	float t = uTime.x, dt = clamp(uTime.z, 0.0, 0.1);
	vec2 rp;
	vec4 c = headCycle(id, uTime.w, uH.x, rp);         // L, age, hold, cycle
	bool fresh = uH.w > 0.5 || st.w < 0.5 || abs(st.z - c.w) > 0.5;
	float use = st.w;
	if (fresh) {
		vec4 M = texture(sTD2DInputs[1], rp);
		float inside = step(0.5, M.r);
		float nearRim = smoothstep(0.97, 0.6, M.g) * inside;
		float a = rnd4(id * 3u + uint(c.w) * 17u, 91u).x;
		use = (inside > 0.5 && a < (0.35 + 2.5 * nearRim) / 2.85) ? 2.0 : 1.0;
	}
	vec2 p;
	if (fresh || c.y < c.z) {
		p = rp + vec2(0.0, bobUV(t));                    // resting on the head
	} else {
		p = st.xy;                                       // flying: peels off slowly, then the stream takes it
		float s = c.y - c.z;
		float ramp = 1.0 - exp(-s / 0.7);
		vec4 r = rnd4(id, 77u);
		vec2 v = curlFlow(p, uH.z) * mix(0.6, 1.3, r.y) * (0.3 + 0.7 * ramp);
		v.x += uH.y * K720 * mix(0.7, 1.3, r.x) * ramp * (1.0 + 1.3 * gustEnv(t));
		p += v * dt;
	}
	fragColor = TDOutputSwizzle(vec4(p, c.w, use));
}
