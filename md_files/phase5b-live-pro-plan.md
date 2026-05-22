# Phase 5b — Live Streaming Pro

> **Maqsad:** Phase 5 da LiveKit asosiy integratsiya + UI strukturasi tayyor. Bu fazada **Zoom / Google Meet darajasidagi professional UX** qo'shiladi: pre-join lobby, device selector, recording controls, quality bar, reactions, background effects.
>
> **Tartib:** S0–S4 (alignment) ✅ → **Phase 5b (live pro)** ⏳ → Phase 6 (Imtihonlar + Proctoring)
>
> **Asosiy reja:** `md_files/ui-alignment-plan.md` §9 da qisqa eslatib o'tilgan edi, endi alohida sprint sifatida ajratildi.

---

## 0. Hozirgi holat (Phase 5 yakuni)

✅ Bajarilgan:
- LiveKit server (Docker, port 7880) ulanmoqda
- Backend: token issuer, session CRUD, recording API, iCal export, attendance tracker
- Frontend `NativeRoom.vue` — LiveKit-client wrapper (defineExpose: toggleAudio/Video/ScreenShare/hangup/sendChat)
- `LiveRoomView.vue` fullscreen shell (wireframe 15) — header, video grid, side panel (Chat/Q&A), bottom controls
- Mic/cam/screen/hangup tugmalari — endi try/catch + toast bilan
- AudioContext user-gesture muammosi tuzatilgan (`ensureAudioStarted()`)

⏳ Yetishmaydi:
- Pre-join lobby (mic/cam test + preview ekrani)
- Device selector (bir nechta qurilma orasidan tanlash)
- Audio level meter (mikrofon kuchi vizual indikator)
- Noise suppression / Echo cancel UI toggle
- Recording start/stop controls (pedagog uchun aniq tugma + REC indikator)
- Network quality bar (`📡 ▰▰▰▰ HD 1080p YAXSHI 28ms`)
- Reactions + hand raise
- Background blur / virtual background
- Mobile responsive (touch controls, orientation-aware)
- Permission denied flow (graceful retry UI)

---

## 1. Sub-sprintlar

| ID | Mavzu | Asosiy fayl(lar) | Kun |
|---|---|---|---|
| **5b.1** | Pre-join lobby | `views/live/LiveLobbyView.vue` (yangi) + route `/app/live/:id/lobby` | 1 |
| **5b.2** | Device selector (mic/speaker/camera) | `components/live/DeviceSelector.vue` (yangi) + `NativeRoom` deviceSwitch API | 1 |
| **5b.3** | Audio level meter | `components/live/AudioLevelMeter.vue` (yangi) + LiveKit `AudioAnalyser` | 0.5 |
| **5b.4** | Recording controls | `LiveRoomView` header'da REC tugmasi + `liveSessionsApi.startRecording`/`stopRecording` ulash | 1 |
| **5b.5** | Network quality bar | `LiveRoomView` bottom controls — wireframe 15 `📡 ▰▰▰▰ HD 1080p YAXSHI 28ms` pattern | 0.5 |
| **5b.6** | Reactions + hand raise | `components/live/ReactionsBar.vue` + LiveKit DataPacket payload | 1 |
| **5b.7** | Background blur / virtual bg | LiveKit Track processor integration | 1 |
| **5b.8** | Mobile responsive | `LiveRoomView` media queries + touch-optimized controls | 1 |
| **5b.9** | Permission denied UX | Lobby va Room ichida permission flow + retry button | 0.5 |
| **5b.10** | i18n 4 locales | Yangi stringlar uz-lat/uz-cyr/ru/en | 0.5 |
| **5b.11** | Smoke test + acceptance | type-check + build + multi-device sinov | 0.5 |

**Jami:** 8–9 kun

---

## 2. Pre-join lobby (5b.1) — wireframe

Yangi sahifa `/app/live/:id/lobby` — `Join now` bosishdan oldin:

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   [VIDEO PREVIEW — kamera]      │   Session     │
│   ┌─────────────────────┐       │   info        │
│   │                     │       │               │
│   │     [your face]     │       │   Title       │
│   │                     │       │   Host: ...   │
│   │                     │       │   Starts in:  │
│   └─────────────────────┘       │   2 min       │
│   [🎙 ON] [📹 ON]               │               │
│                                  │   N kishi     │
│   Mic:   [Default ▼]            │   ulangan     │
│   Cam:   [Default ▼]            │               │
│   Speaker: [Default ▼]          │   [Join now]  │
│                                  │               │
└─────────────────────────────────────────────────┘
```

**Tarkibi:**
- Video preview (kamera yoqilgan bo'lsa)
- Mic/cam toggle (lokal preview, hali room'ga ulanmagan)
- Audio level meter (mikrofon kuchi vizual)
- Device dropdown'lar (Mic / Cam / Speaker)
- Session metadata (title, host, starts in, participant count)
- "Join now" big button

**Backend talab yo'q** — barchasi browser API (`navigator.mediaDevices.enumerateDevices()` + `getUserMedia({audio, video})`).

---

## 3. Device selector (5b.2)

`navigator.mediaDevices.enumerateDevices()` orqali ro'yxat olamiz, LiveKit'ning `setMediaDeviceId()` API'si bilan switch qilamiz.

Live Room ichida controls bar'da dropdown:
```
[🎙 ▼ Mic: MacBook Pro Microphone]
```

---

## 4. Recording controls (5b.4)

Wireframe 15 ga ko'ra recording tugmasi **header'da** (chap top), pastki controls'da emas. Pedagog uchun:

```
[● REC] / [⏹ Yozib olishni to'xtatish]
```

Backend allaqachon tayyor — `liveSessionsApi.startRecording(sessionId)` / `stopRecording(sessionId)`.

REC indikator: header'da qizil pulsing dot + `REC 12:34`.

---

## 5. Network quality bar (5b.5)

Wireframe 15 pattern (pastki controls o'ng tarafi):

```
📡 ▰▰▰▰ HD 1080p YAXSHI 28ms
```

Manba: LiveKit `ConnectionQuality` event + `Room.engine.client.rtt`.

---

## 6. Reactions + hand raise (5b.6)

LiveKit DataPacket orqali:
```ts
{ kind: 'reaction', emoji: '👏' | '👍' | '❤️' | '😂' | '🎉' }
{ kind: 'hand_raise', up: true | false }
```

UI: kichik floating button strip controls yonida; bosilganda emoji 3-4 sekund video grid'da animatsiya qiladi.

---

## 7. Background blur (5b.7)

LiveKit `BackgroundProcessor` (TFLite / MediaPipe). Settings menu'da: None / Blur / Virtual image.

Performance: faqat desktop'da yoqamiz, mobile'da disabled (CPU og'irligi).

---

## 8. Mobile responsive (5b.8)

Wireframe 15 desktop optimized. Mobile uchun:
- Header: stacked (LIVE pill + timer top, title separate row)
- Video grid: 1 column (main full-width, thumbnails scroll horizontal)
- Side panel: drawer (`UiDrawer`), default closed
- Controls: bottom bar full-width, 56px tall (touch-friendly)

Media query: `@media (max-width: 768px)`.

---

## 9. Permission denied UX (5b.9)

Hozir: toast "Mikrofon: Permission denied" — foydalanuvchi nima qilishini bilmaydi.

Pro UX:
1. Lobby ichida permission so'ralsa va denied bo'lsa — banner:
   ```
   ⚠ Mikrofon va kameraga ruxsat berilmagan.
   Brauzer manzil panelidagi 🔒 ikonkasini bosib "Allow" tanlang
   va sahifani qaytadan yuklang.
   ```
2. Retry button (yangi getUserMedia call)
3. Skip option ("Audio'siz kuzating") — listen-only mode

---

## 10. i18n yangi kalitlar (5b.10)

`live.*` namespace'iga qo'shiladi:

- `lobby_title`, `lobby_join`, `lobby_audio_only`, `lobby_preview_off`
- `device_mic`, `device_cam`, `device_speaker`, `device_default`
- `audio_level_low`, `audio_level_high`
- `recording_start`, `recording_stop`, `recording_indicator`
- `quality_hd`, `quality_sd`, `quality_rtt`
- `reaction_clap`, `reaction_thumbs`, `reaction_heart`, `reaction_laugh`, `reaction_celebrate`
- `hand_raise`, `hand_lower`
- `bg_none`, `bg_blur`, `bg_image`
- `permission_denied_title`, `permission_denied_help`, `permission_retry`, `permission_listen_only`

**Talab:** 4 ta locale × ~25 yangi kalit = 100 yangi tarjima.

---

## 11. Acceptance kriteriyalari (Phase 6 ga o'tish sharti)

1. **Lobby ekrani ishlaydi:** Join bosishdan oldin mic/cam test + device selector
2. **Recording pedagog uchun:** REC tugmasi → backend `start_recording` → indikator yonadi → "Stop" bosilganda saqlanadi va `recording_url` to'ldiriladi
3. **Network quality bar:** real-time RTT + bitrate ko'rsatadi
4. **Reactions:** kamida 5 ta emoji, hand raise toggle, barcha ishtirokchilarga ko'rinadi
5. **Background blur:** desktop'da yoqilsa, video grid'da haqiqatda blur effect ishlaydi
6. **Mobile (Chrome iOS / Safari iOS):** 375px enga vertikal portretda controls + video grid normal ko'rinadi
7. **Permission denied:** denied bo'lsa user'ga aniq help banner + retry tugmasi
8. **i18n 4 locale parity OK**
9. **Smoke:** `vue-tsc -b` exit 0 · `build:user` exit 0 · HTTP routes 200

---

## 12. Boshqa fazaga qoldirilgan (out of scope)

| Element | Kuyingi faza | Sabab |
|---|---|---|
| Real-time captions / STT | Phase 9 (AI/Analytics) | Speech-to-text servisi kerak (Whisper/Vosk/Yandex) — alohida integration |
| Breakout rooms | Phase 5c (kelgusi sub-faza) | Multi-room logic backend talab qiladi (session split) |
| Cloud recording (S3-compatible storage) | Phase 7 (Deploy) | MinIO production setup'ga bog'liq |
| Live captions translation | Phase 9 | STT + translate pipeline |

---

## 13. Dependencies

- LiveKit-client `^2.18.9` (mavjud)
- `@mediapipe/tasks-vision` — background blur uchun (yangi)
- LiveKit Egress (recording) — backend allaqachon ulagan

---

## 14. Reference wireframes

- `15-live-class.html` — asosiy live shell (mavjud)
- (Yangi) Pre-join lobby uchun wireframe yoq — Zoom/Meet pattern'ini ko'chiramiz, design-system'ga mos qora-oq monoxrom.

---

*Bu reja foydalanuvchi tasdiqlagandan keyin sprint'ma-sprint bajariladi. Har sub-sprint oxirida side-by-side test (real ikkita brauzer instance) + foydalanuvchi tasdig'i bilan keyingi sub-sprint'ga o'tiladi.*
