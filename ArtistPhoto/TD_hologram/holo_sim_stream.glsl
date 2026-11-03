// holo_sim_stream - the stream: one texel = one particle (rgba32float, fed back through stream_fb).
// state: xy = position (UV), z = its speed factor, w = how strongly the swirls carry it.
// Particles enter on the left and leave on the right, carried by the current and the curl-noise swirls; while the
// face is present they slow down inside the head (they gather there, so the head shows). A gust on hits.
// input 0 = the state, input 1 = holo_maps (a = where the stream slows down)
uniform vec4 uS;   // Streamspeed (px/s at 720 high), Headslow, Turbulence, reset
out vec4 fragColor;
void main() {
	ivec2 px = ivec2(gl_FragCoord.xy);
	ivec2 res = textureSize(sTD2DInputs[0], 0);
	uint id = uint(px.y * res.x + px.x);
	vec4 st = texelFetch(sTD2DInputs[0], px, 0);
	vec4 h = rnd4(id, 11u);
	float t = uTime.x, dt = clamp(uTime.z, 0.0, 0.1);
	if (uS.w > 0.5 || st.w < 0.01) {                  // start: scattered over the whole frame, so it flows at once
		fragColor = TDOutputSwizzle(vec4(h.x * 1.04 - 0.02, h.y * 1.08 - 0.04, mix(0.75, 1.3, h.z), mix(0.6, 1.4, h.w)));
		return;
	}
	vec2 p = st.xy;
	if (p.x > 1.012 || p.y < -0.08 || p.y > 1.08) {   // left the frame: enter again on the left
		vec4 r = rnd4(id, uint(uBur.z) * 977u + 5u);
		fragColor = TDOutputSwizzle(vec4(-r.x * 0.04, r.y * 1.08 - 0.04, st.z, st.w));
		return;
	}
	float pres = presence(t), gust = gustEnv(t);
	float sl = texture(sTD2DInputs[1], vec2(p.x, p.y - bobUV(t))).a;
	vec2 v = curlFlow(p, uS.z) * st.w;
	v.x += uS.x * K720 * st.z * (1.0 - uS.y * pres * sl) * (1.0 + 1.3 * gust);
	p += v * dt;
	fragColor = TDOutputSwizzle(vec4(p, st.z, st.w));
}
