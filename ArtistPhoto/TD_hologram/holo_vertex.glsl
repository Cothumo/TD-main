// holo_vertex - particle sprites (GLSL MAT vertex shader, one instance per particle; additive into a float buffer).
// Each particle takes its light from the glow map at its position, so the stream lights up where it passes through
// the face. Stream particles are short streaks along their motion; the head's own particles are trembling dots while
// they rest, then streaks that carry the light of the face they lifted off (only if it was visible then).
uniform sampler2D sState;
uniform sampler2D sGlow;
uniform vec4 uV;   // kind (0 = stream, 1 = head), Particlesize (px at 720 high), output height (px), Particlehold (s)
uniform vec4 uW;   // Streamspeed (px/s at 720 high), 0, 0, 0
out Vertex {
	vec4 col;
	vec2 q;
} oVert;

void main() {
	int id = TDInstanceID();
	ivec2 rs = textureSize(sState, 0);
	vec4 st = texelFetch(sState, ivec2(id % rs.x, id / rs.x), 0);
	uint uid = uint(id);
	float t = uTime.x, frame = uBur.z, Hpx = uV.z;
	vec4 fz = rnd4(uid, uint(frame) * 3001u + 41u);      // new every frame: twinkle
	vec2 p = st.xy;
	float w = 0.0, len = 0.0;
	float size = max(uV.y * Hpx / 720.0, 0.5);
	float movePx = uW.x / 720.0 * Hpx * uTime.z;          // how far the stream moves in one frame (px)
	if (uV.x < 0.5) {
		float edge = smoothstep(-0.01, 0.01, p.x) * smoothstep(1.012, 0.99, p.x);
		w = texture(sGlow, p).r * edge * (0.35 + 1.3 * fz.x * fz.x);     // a few bright sparks
		len = movePx * st.z;
	} else if (st.w > 1.5) {
		vec2 rp;
		vec4 c = headCycle(uid, uTime.w, uV.w, rp);
		if (c.y < c.z) {                                  // resting: trembles, shows only while the face is present
			p += (fz.zw - 0.5) * 1.2 / Hpx;
			w = 0.6 * presence(t) * texture(sGlow, p).r * min(c.y / 0.1, 1.0) * (0.3 + 1.2 * fz.x * fz.x);
		} else {                                          // flying: the light of the face it lifted off
			float s = c.y - c.z;
			float u = s / max(c.x - c.z, 0.01);
			w = presence(t - s) * texture(sGlow, p).r * pow(max(1.0 - u, 0.0), 0.8) * (0.7 + 0.6 * fz.x);
			len = movePx * (1.0 - exp(-s / 0.7));
		}
	}
	if (w <= 1e-4) {
		gl_Position = vec4(2.0, 2.0, 2.0, 1.0);           // outside the clip volume
		oVert.col = vec4(0.0);
		oVert.q = vec2(0.0);
		return;
	}
	vec2 corner = P.xy * 2.0;                              // Rectangle SOP 1 x 1 -> -1..1
	float hx = max(size, 0.5 * len + 0.5 * size), hy = size;
	vec2 shift = vec2(-0.5 * len, 0.0);                    // the streak trails behind the particle
	vec2 px2ndc = vec2(2.0 / Hpx, 2.0 / Hpx);             // square output
	gl_Position = vec4(p * 2.0 - 1.0 + (corner * vec2(hx, hy) + shift) * px2ndc, 0.5, 1.0);
	float amount = w / (0.87 * hx * hy);                    // the same light whatever the sprite's size
	oVert.col = vec4(vec3(amount), 1.0);
	oVert.q = corner;
}
