// Ambient Ink - ink on paper (GLSL TOP). Input 0 = accumulated ink (r = amount, g = amount x age, b = spray ink),
// input 1 = blurred copy (dissolved halo). The hi-hat spray is laid over the main ink in the accent colour. Transmittance exp(-ink) gives opaque black cores with soft grey edges; old ink shifts
// towards the dilute colour; the paper gets texture, marks, a side light, grain and a vignette.
uniform vec4 uF;   // frame, Opacity, Diffusion, Grain
uniform vec4 uG;   // arc, level, Reactivity, Invert
uniform vec4 uH;   // Paper r, g, b, Vignette
uniform vec4 uI;   // Ink r, g, b, Paperdetail
uniform vec4 uJ;   // Dilute r, g, b, Light
uniform vec4 uK;   // aspect (W/H), Lightangle (deg), vib (unstable-sound envelope), Vibration
uniform vec4 uL;   // Accent r, g, b, 0
uniform vec4 uM;   // dis (percussion-hit envelope), dis_id (hit counter), Disruption, 0

out vec4 fragColor;

float hash12(vec2 p)
{
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vnoise(vec2 p)
{
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x), mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p)
{
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) {
		s += a * vnoise(p);
		p = p * 2.03 + vec2(17.1, 9.7);
		a *= 0.5;
	}
	return s;
}

void main()
{
	vec2 uv = vUV.st;
	vec2 res = vec2(textureSize(sTD2DInputs[0], 0));
	vec2 a = vec2(uK.x, 1.0);
	float react = uG.z;

	// vibration: on unstable sounds the ink shakes - per-frame jitter + a fast oscillation, rows wobble a little,
	// and a faint second image trails the shake (the paper stays still, only the ink trembles)
	float vib = clamp(uK.z * uK.w, 0.0, 3.0);
	vec2 off = vec2(0.0);
	if (vib > 0.001) {
		float fr = uF.x;
		vec2 j = vec2(hash12(vec2(fr, 1.37)), hash12(vec2(fr, 7.91))) * 2.0 - 1.0;
		vec2 s = vec2(sin(fr * 2.71), cos(fr * 3.37));
		off = (j * 0.65 + s * 0.35) * vib * 16.0 / res;
		off.x += sin(uv.y * res.y * 0.045 + fr * 1.9) * vib * 5.0 / res.x;
	}
	// disruption: each percussion hit tears the ink into horizontal strips that slide sideways (a new pattern per hit),
	// a few strips drop out to paper and a stuttered echo of the ink jumps down for a moment
	float dis = clamp(uM.x * uM.z, 0.0, 3.0);
	float drop = 0.0;
	vec2 doff = vec2(0.0);
	if (dis > 0.003) {
		float hid = uM.y;
		float bh = mix(6.0, 46.0, hash12(vec2(hid, 3.1)));                    // strip height in px
		float strip = floor((uv.y * res.y + hash12(vec2(hid, 5.7)) * 50.0) / bh);
		float r = hash12(vec2(strip, hid * 1.31 + 0.5));
		float mv = step(0.45, r) * (hash12(vec2(strip, hid + 9.2)) * 2.0 - 1.0);
		doff.x = mv * mix(20.0, 90.0, hash12(vec2(strip, hid + 2.6))) * dis / res.x;
		float xa = hash12(vec2(strip, hid + 4.4)), xl = mix(0.15, 0.5, hash12(vec2(strip, hid + 6.1)));
		float seg = smoothstep(xa - 0.03, xa + 0.03, uv.x) * smoothstep(xa + xl + 0.03, xa + xl - 0.03, uv.x);
		drop = step(0.92, r) * seg * dis * 0.6;                              // part of a strip thins out
		off += doff;
	}
	vec3 ink = texture(sTD2DInputs[0], uv + off).rgb;
	vec3 halo = texture(sTD2DInputs[1], uv + off).rgb;
	if (dis > 0.003) {
		vec2 eo = vec2(0.0, (18.0 + 30.0 * hash12(vec2(uM.y, 8.8))) / res.y);
		float ew = clamp(0.45 * dis, 0.0, 0.7);
		ink = max(ink, texture(sTD2DInputs[0], uv + off + eo).rgb * ew);
		ink *= 1.0 - clamp(drop, 0.0, 0.85);
		halo *= 1.0 - clamp(drop, 0.0, 0.85);
	}
	if (vib > 0.001) {
		float gw = clamp(0.45 * vib, 0.0, 0.6);
		ink = mix(ink, texture(sTD2DInputs[0], uv - off * 1.6).rgb, gw);
		halo = mix(halo, texture(sTD2DInputs[1], uv - off * 1.6).rgb, gw);
	}
	float dens = ink.r + halo.r * uF.z * 0.6;
	float ageR = clamp((ink.g + halo.g * uF.z * 0.6) / max(dens, 1e-4), 0.0, 1.0);
	float T = exp(-dens * uF.y * (0.9 + 0.2 * uG.x * react));      // light passing through the ink

	// paper: cloudy texture, fibres and a few fixed marks
	vec2 pu = uv * a;
	float tex = fbm(pu * 3.0) - 0.5;
	float fib = vnoise(pu * vec2(180.0, 60.0)) - 0.5;
	vec3 paper = uH.rgb * (1.0 - uI.w * (0.10 * tex + 0.03 * fib));
	float mark = step(0.9988, hash12(floor(uv * res / 2.0)));
	mark += step(0.985, vnoise(pu * 22.0)) * 0.5;
	paper *= 1.0 - uI.w * 0.35 * clamp(mark, 0.0, 1.0);

	// side light across the paper, breathing slightly with the music
	float la = radians(uK.y);
	vec2 ld = vec2(cos(la), sin(la));
	float light = 0.93 + 0.30 * uJ.w * dot(ld, (uv - 0.5) * a) - 0.12 * uJ.w * dot((uv - 0.5) * a, (uv - 0.5) * a);
	light *= 1.0 + 0.04 * react * (uG.y - 0.5);

	vec3 inkCol = mix(uI.rgb, uJ.rgb, pow(ageR, 0.8));
	vec3 c = paper * light * T + inkCol * (1.0 - T);
	float Ts = exp(-(ink.b + halo.b * uF.z * 0.4) * uF.y * 1.3);   // spray droplets in the accent ink
	c = c * Ts + uL.rgb * (1.0 - Ts);

	float gr = hash12(gl_FragCoord.xy + fract(uF.x * 0.6180339) * 1000.0) - 0.5;
	c += gr * uF.w * 0.06;
	vec2 v = (uv - 0.5) * a;
	c *= clamp(1.0 - uH.w * dot(v, v) * 0.9, 0.0, 1.0);
	c = mix(c, 1.0 - c, uG.w);
	fragColor = TDOutputSwizzle(vec4(clamp(c, 0.0, 1.0), 1.0));
}
