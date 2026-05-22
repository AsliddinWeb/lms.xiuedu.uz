# 05. Content Management Moduli

## Maqsad

Ta'lim materiallarini yaratish, saqlash va yetkazib berish. SCORM/xAPI standartlariga moslik. OʻzDSt 36.2030 standartiga muvofiqlik.

## Funksional talablar

### 1. Kontent turlari

| Tur | Format | Tavsifi |
|-----|--------|---------|
| **Matn (Text)** | Rich text (TipTap) | Ma'ruza matnlari |
| **Video** | MP4, MOV → HLS | Yozib olingan darslar |
| **Audio** | MP3, OGG | Podkast, izoh |
| **Taqdimot** | PDF, PPTX | Slaydlar |
| **Hujjat** | PDF, DOCX | Qo'shimcha materiallar |
| **SCORM** | ZIP (1.2 / 2004) | Standart paketlar |
| **xAPI / Tin Can** | ZIP | Zamonaviy standart |
| **Interaktiv** | H5P, custom | Kvizlar, interaktiv |
| **Havola** | URL | Tashqi resurs |
| **Code playground** | Embed | Kod yozish (programlash) |

### 2. Video kontent talablari

- Maksimum hajm: 5 GB / 1 video
- Avtomatik transkodlash: 360p, 480p, 720p, 1080p
- HLS streaming (adaptive bitrate)
- Subtitr generatsiyasi (Whisper AI)
- Video tezligi: 0.5x — 2x
- Watermark (talaba ID)
- Skip / rewind nazorati
- View progress saqlanadi

### 3. SCORM/xAPI

- **SCORM 1.2** va **2004** qo'llab-quvvatlanadi
- Avtomatik validation (paket struktura)
- Player integratsiyasi
- Progress, score sync
- xAPI uchun Learning Record Store (LRS)

### 4. Elektron O'quv-Metodik Majmua (EOʻMM)

OʻzDSt 36.2030 talablariga muvofiq, har bir fan uchun EOʻMM:
- Fan dasturi
- Ma'ruza matnlari
- Amaliy/laboratoriya ishlari
- Mustaqil ish topshiriqlari
- Test va imtihon savollari
- Adabiyotlar ro'yxati
- Glossariy

### 5. Versiyalash

- Har qanday o'zgarish — yangi versiya
- Eski versiyalar arxivlanadi
- Versiyalararo solishtirish (diff)
- Talabaga qaysi versiya ko'rsatilishi sozlanadi

### 6. Kontent qidiruvi

- Full-text qidiruv (OpenSearch)
- Filtr: tur, fan, til, sana
- Tayinlash: kurslarga
- Tag / kategoriyalash

### 7. Hamkorlik

- Bir fanni bir necha pedagog yaratishi mumkin
- Tahrirlash huquqlari
- Sharhlash (review)
- Tasdiqlash workflow (kafedra mudiri tasdiqlaydi)

## API Endpoints

```
# Kontent
GET    /api/v1/content                        # ro'yxat
POST   /api/v1/content                        # yaratish
GET    /api/v1/content/{id}
PATCH  /api/v1/content/{id}
DELETE /api/v1/content/{id}
POST   /api/v1/content/{id}/duplicate
POST   /api/v1/content/{id}/publish
POST   /api/v1/content/{id}/unpublish

# Versiyalar
GET    /api/v1/content/{id}/versions
POST   /api/v1/content/{id}/versions          # yangi versiya
GET    /api/v1/content/{id}/versions/{version}
POST   /api/v1/content/{id}/restore/{version}

# Fayl yuklash
POST   /api/v1/content/upload                 # multipart upload
POST   /api/v1/content/upload/chunk           # katta fayllar uchun chunked
GET    /api/v1/content/upload/{upload_id}/status
POST   /api/v1/content/upload/{upload_id}/complete

# Video
POST   /api/v1/content/video                  # yuklash → transkodlash
GET    /api/v1/content/video/{id}/manifest    # HLS manifest
GET    /api/v1/content/video/{id}/transcript

# SCORM
POST   /api/v1/content/scorm/upload           # ZIP yuklash
POST   /api/v1/content/scorm/validate         # struktura tekshirish
GET    /api/v1/content/scorm/{id}/launch      # ishga tushirish

# xAPI / LRS
POST   /api/v1/lrs/statements                 # statement saqlash
GET    /api/v1/lrs/statements                 # statementlarni olish

# EOʻMM
POST   /api/v1/eomm                           # majmua yaratish
GET    /api/v1/eomm/{id}
GET    /api/v1/eomm/{id}/standard-check       # OʻzDSt moslik tekshiruvi

# Qidiruv
GET    /api/v1/content/search?q=...
```

## Database modellari

```sql
-- Kontent
CREATE TABLE content_items (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(30) NOT NULL,                 -- 'text', 'video', 'scorm', 'pdf', etc.
    title VARCHAR(500) NOT NULL,
    description TEXT,
    
    subject_id BIGINT REFERENCES subjects(id),
    department_id BIGINT REFERENCES departments(id),
    
    -- Mualliflar
    author_id BIGINT REFERENCES users(id),
    co_authors BIGINT[],                       -- co-author IDlari
    
    -- Kontent
    content_data JSONB,                        -- text uchun
    file_url TEXT,                             -- fayl uchun
    file_size BIGINT,
    mime_type VARCHAR(100),
    duration_seconds INT,                      -- video/audio uchun
    
    -- Til va metadata
    language VARCHAR(10) DEFAULT 'uz-lat',
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    
    -- Versiyalash
    version VARCHAR(20) DEFAULT '1.0',
    parent_id BIGINT REFERENCES content_items(id),
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',        -- 'draft', 'review', 'published', 'archived'
    published_at TIMESTAMP,
    
    -- Auditing
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_content_subject ON content_items(subject_id);
CREATE INDEX idx_content_author ON content_items(author_id);
CREATE INDEX idx_content_status ON content_items(status);
CREATE INDEX idx_content_search ON content_items USING gin(to_tsvector('simple', title || ' ' || COALESCE(description, '')));

-- Video kontent (alohida jadval)
CREATE TABLE video_assets (
    id BIGSERIAL PRIMARY KEY,
    content_id BIGINT REFERENCES content_items(id) ON DELETE CASCADE,
    original_url TEXT,                         -- asl fayl
    hls_manifest_url TEXT,                     -- master.m3u8
    thumbnail_url TEXT,
    duration_seconds INT,
    transcoding_status VARCHAR(20),            -- 'pending', 'processing', 'done', 'failed'
    qualities JSONB,                           -- [{quality: '720p', url: '...'}]
    transcript TEXT,                           -- Whisper'dan
    transcript_language VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- SCORM paketlar
CREATE TABLE scorm_packages (
    id BIGSERIAL PRIMARY KEY,
    content_id BIGINT REFERENCES content_items(id) ON DELETE CASCADE,
    version VARCHAR(10),                       -- '1.2', '2004'
    package_url TEXT,                          -- ZIP fayl
    extracted_path TEXT,                       -- ekstraktlangan papka
    launch_url TEXT,                           -- index.html
    manifest JSONB,                            -- imsmanifest.xml parse qilingan
    organizations JSONB,
    resources JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- xAPI Learning Record Store
CREATE TABLE xapi_statements (
    id BIGSERIAL PRIMARY KEY,
    statement_id UUID UNIQUE NOT NULL,
    actor JSONB NOT NULL,                      -- aktor (talaba)
    verb JSONB NOT NULL,                       -- harakat (started, completed)
    object JSONB NOT NULL,                     -- obyekt (kontent)
    result JSONB,                              -- natija (score, success)
    context JSONB,
    timestamp TIMESTAMP DEFAULT NOW(),
    stored_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_xapi_actor ON xapi_statements USING gin(actor);
CREATE INDEX idx_xapi_timestamp ON xapi_statements(timestamp DESC);

-- EOʻMM
CREATE TABLE eomm (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT UNIQUE REFERENCES subjects(id),
    title VARCHAR(500) NOT NULL,
    structure JSONB,                           -- bo'limlar tuzilmasi
    standard_compliance JSONB,                 -- OʻzDSt 36.2030 tekshiruv
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE eomm_components (
    id BIGSERIAL PRIMARY KEY,
    eomm_id BIGINT REFERENCES eomm(id) ON DELETE CASCADE,
    type VARCHAR(50),                          -- 'lecture', 'practice', 'self_study', 'test'
    title VARCHAR(500),
    content_ids BIGINT[],                      -- bog'liq content_items
    order_index INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Video transkodlash workflow

```python
# app/workers/video.py
from celery import Task
import ffmpeg

@celery_app.task(bind=True, max_retries=3)
def transcode_video(self, video_id: int):
    video = get_video(video_id)
    
    try:
        # 1. Status: processing
        update_status(video_id, "processing")
        
        # 2. Asl faylni yuklab olish (MinIO'dan)
        input_path = download_from_minio(video.original_url)
        
        # 3. Sifatlar uchun transkodlash
        qualities = [
            {"name": "360p", "height": 360, "bitrate": "800k"},
            {"name": "480p", "height": 480, "bitrate": "1500k"},
            {"name": "720p", "height": 720, "bitrate": "3000k"},
            {"name": "1080p", "height": 1080, "bitrate": "5000k"},
        ]
        
        outputs = []
        for q in qualities:
            output = transcode_quality(input_path, q)
            url = upload_to_minio(output)
            outputs.append({"quality": q["name"], "url": url})
        
        # 4. HLS manifest
        manifest = create_hls_manifest(outputs)
        manifest_url = upload_to_minio(manifest)
        
        # 5. Thumbnail
        thumbnail = generate_thumbnail(input_path, time=10)
        thumbnail_url = upload_to_minio(thumbnail)
        
        # 6. Transcript (Whisper)
        transcript = transcribe(input_path)
        
        # 7. Saqlash
        update_video(
            video_id,
            hls_manifest_url=manifest_url,
            thumbnail_url=thumbnail_url,
            qualities=outputs,
            transcript=transcript,
            transcoding_status="done",
        )
        
    except Exception as e:
        update_status(video_id, "failed")
        raise self.retry(exc=e, countdown=60)
```

## SCORM player

```vue
<!-- components/content/ScormPlayer.vue -->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useXAPI } from '@/composables/useXAPI'

const props = defineProps<{ packageId: number }>()
const xapi = useXAPI()
const iframeRef = ref<HTMLIFrameElement>()

// SCORM API simulator
const scormAPI = {
  Initialize: () => {
    xapi.send({ verb: 'initialized', object: props.packageId })
    return 'true'
  },
  GetValue: (key: string) => {
    // local storage'dan o'qish
    return localStorage.getItem(`scorm_${props.packageId}_${key}`) || ''
  },
  SetValue: (key: string, value: string) => {
    localStorage.setItem(`scorm_${props.packageId}_${key}`, value)
    
    // Important values'ni server'ga yuborish
    if (key === 'cmi.completion_status' && value === 'completed') {
      xapi.send({ verb: 'completed', object: props.packageId })
    }
    if (key === 'cmi.score.scaled') {
      xapi.send({ 
        verb: 'scored', 
        object: props.packageId,
        result: { score: { scaled: parseFloat(value) } }
      })
    }
    return 'true'
  },
  Commit: () => 'true',
  Terminate: () => {
    xapi.send({ verb: 'terminated', object: props.packageId })
    return 'true'
  },
}

onMounted(() => {
  // SCORM API'ni window'ga qo'yish (iframe shu yerdan oladi)
  ;(window as any).API_1484_11 = scormAPI  // SCORM 2004
  ;(window as any).API = scormAPI           // SCORM 1.2
})
</script>

<template>
  <iframe
    ref="iframeRef"
    :src="`/api/v1/content/scorm/${packageId}/launch`"
    class="w-full h-screen border-0"
    allow="autoplay; fullscreen"
  />
</template>
```

## OʻzDSt 36.2030 moslik tekshiruvi

```python
# app/modules/content/standard_compliance.py

class OzDStCompliance:
    """OʻzDSt 36.2030 talablariga moslik tekshiruvi"""
    
    REQUIRED_COMPONENTS = [
        "course_program",          # Fan dasturi
        "lecture_materials",       # Ma'ruza matnlari
        "practical_works",         # Amaliy ishlar
        "self_study_tasks",        # Mustaqil ish
        "tests_questions",         # Test savollari
        "literature_list",         # Adabiyotlar
        "glossary",                # Lug'at
    ]
    
    async def check(self, eomm_id: int) -> dict:
        eomm = await get_eomm(eomm_id)
        components = await get_eomm_components(eomm_id)
        
        missing = []
        for required in self.REQUIRED_COMPONENTS:
            if not any(c.type == required for c in components):
                missing.append(required)
        
        return {
            "compliant": len(missing) == 0,
            "missing_components": missing,
            "checked_at": datetime.utcnow(),
        }
```

## Acceptance kriteriyalar

- [ ] Barcha kontent turlari yaratish
- [ ] Video upload va HLS transkodlash
- [ ] Subtitr (Whisper) generatsiyasi
- [ ] SCORM 1.2 va 2004 qo'llab-quvvatlash
- [ ] xAPI / LRS
- [ ] EOʻMM yaratish (OʻzDSt moslik tekshiruvi)
- [ ] Versiyalash
- [ ] Kontent qidiruvi (OpenSearch)
- [ ] Hamkorlik (multiple authors)
- [ ] Tasdiqlash workflow
- [ ] Frontend kontent yaratuvchi (TipTap)
- [ ] Test coverage ≥ 80%
