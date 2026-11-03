// Scenes - between the NIN stage and the sphere (ink_layer -> nin_stage -> scenes -> sphere -> viewer).
//   - Backlit haze (Cold and Black and Infinite): one soft light far behind drifting haze; the scene's shapes become
//     dark forms against it. The pads (Stems) thicken the haze.
//   - Live camera silhouette (any scene): the performer as a dark figure in the scene, the picture flowing round the
//     body, faint echoes trailing its movement.
// Grey only, nothing flashes. input 0 = the picture (nin_stage/OUT), input 1 = silhouette (r = body, g = trail).
uniform vec4 uA;   // time (s), -, Backlight (0..1), Silhouette (0..1)
uniform vec4 uB;   // pads (0..1, smoothed), level (0..1, smoothed), Hazedensity, Lightsize
uniform vec4 uC;   // light x, light y (0..1), Silhouettedark, Siltrail
uniform vec4 uD;   // Silscale, Silx, Sily (offset), Mirror (0/1)
uniform vec4 uE;   // -, -, -, Silflow
out vec4 fragColor;
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 pic(vec2 uv) { uv = 1.0 - abs(1.0 - mod(abs(uv), 2.0)); return texture(sTD2DInputs[0], clamp(uv, vec2(0.001), vec2(0.999))).rgb; }

// the silhouette at a frame position: the camera fills the frame height (cropped at the sides), scaled / moved / mirrored
vec2 sil(vec2 uv) {
	vec2 r1 = uTD2DInfos[1].res.zw;
	float Ac = r1.x / max(r1.y, 1.0);
	float Ao = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
	vec2 c = uv - 0.5 - uD.yz;
	c /= max(uD.x, 0.05);
	c.x *= Ao / max(Ac, 0.01);
	c += 0.5;
	if (uD.w > 0.5) c.x = 1.0 - c.x;
	if (c.x < 0.0 || c.y < 0.0 || c.x > 1.0 || c.y > 1.0) return vec2(0.0);
	vec2 e = smoothstep(0.0, 0.04, c) * smoothstep(0.0, 0.04, 1.0 - c);       // no hard camera borders
	return texture(sTD2DInputs[1], c).rg * e.x * e.y;
}

void main() {
	vec2 uv = vUV.st;
	float t = uA.x;
	vec2 RS = uTDOutputInfo.res.zw;
	float asp = RS.x / RS.y;
	float paper = smoothstep(0.35, 0.75, (luma(pic(vec2(0.2, 0.25))) + luma(pic(vec2(0.8, 0.75))) + luma(pic(vec2(0.5, 0.1)))) / 3.0);
	float SIL = clamp(uA.w, 0.0, 1.0);

	// ---- the picture flows round the body: pushed out along the silhouette's edge and dragged along it
	vec2 s0 = vec2(0.0), suv = uv;
	float edge = 0.0;
	if (SIL > 0.001) {
		s0 = sil(uv);
		vec2 px = vec2(0.006, 0.006 * asp);
		float gx = sil(uv + vec2(px.x, 0.0)).r - sil(uv - vec2(px.x, 0.0)).r;
		float gy = sil(uv + vec2(0.0, px.y)).r - sil(uv - vec2(0.0, px.y)).r;
		vec2 g = vec2(gx, gy);
		edge = clamp(length(g) * 2.0, 0.0, 1.0);
		float fl = uE.w * SIL;
		suv -= g * 0.035 * fl;
		suv += vec2(-gy, gx) * 0.05 * fl * (fbm(uv * 3.0 + vec2(t * 0.15, -t * 0.1)) - 0.5) * 2.0;
	}
	vec3 col = pic(suv);

	// ---- backlit haze: a soft light far behind drifting haze; the scene's shapes are dark forms against it
	float B = clamp(uA.z, 0.0, 1.0);
	float lightAt = 0.0;
	if (B > 0.001) {
		vec2 L = uC.xy + 0.035 * vec2(sin(t * 0.05), cos(t * 0.037));
		vec2 dl = (uv - L) * vec2(1.0, 1.0 / asp);
		float r = length(dl);
		float size = max(uB.w, 0.02);
		float hz = clamp(uB.z * (0.55 + 0.9 * uB.x), 0.0, 2.5);
		float f1 = fbm(uv * vec2(2.0, 2.0 / asp) + vec2(t * 0.01, -t * 0.022));
		float f2 = fbm(uv * vec2(4.5, 4.5 / asp) + vec2(-t * 0.018, -t * 0.04) + f1 * 1.5);
		float fog = clamp(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0.0, 1.0);
		float core = exp(-r * r / (size * size * 0.06)) * (1.0 - 0.55 * min(hz, 1.0));  // the source, softened by thick haze
		float glow = exp(-r / size);
		float scatter = exp(-r / (size * 2.2)) * fog * hz;                         // light caught in the haze
		float light = min(core * 0.7 + glow * 0.22 + scatter * 0.36, 0.8) * (0.88 + 0.12 * uB.y);
		float lp = luma(col);
		float occ = mix(smoothstep(0.06, 0.4, lp), smoothstep(0.85, 0.45, lp), paper);
		vec3 bl = vec3(light) * (1.0 - 0.88 * occ) + vec3(0.025) * fog * hz;
		col = mix(col, bl, B);
		lightAt = light * B;
	}

	// ---- the live silhouette in front of it all: a dark figure, faint echoes of its movement
	if (SIL > 0.001) {
		float body = clamp(s0.r, 0.0, 1.0) * SIL;
		float tr = clamp(s0.g - s0.r, 0.0, 1.0) * SIL * uC.w;
		col *= 1.0 - 0.35 * tr;
		col = mix(col, col * 0.05, body * uC.z);
		col += vec3(0.5) * edge * lightAt * SIL * (1.0 - body);   // against the backlight its outline catches a little light
	}
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
