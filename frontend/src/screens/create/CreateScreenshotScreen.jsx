import { useRef, useState } from 'react';
import { Icon } from '../../components/Icon.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED = /^image\/(jpeg|jpg|png|webp)$/i;

function formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(2)} МБ`;
}

// Сжимает изображение в JPEG не больше 1280×720 с заданным quality.
// Используется чтобы data:URL влезал в БД и не таскал по сети мегабайты.
function compressToDataUrl(file, maxW = 1280, maxH = 720, quality = 0.82) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const ratio = Math.min(maxW / img.width, maxH / img.height, 1);
        const w = Math.round(img.width * ratio);
        const h = Math.round(img.height * ratio);
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = () => reject(new Error('Не удалось прочитать изображение'));
      img.src = reader.result;
    };
    reader.onerror = () => reject(new Error('Не удалось прочитать файл'));
    reader.readAsDataURL(file);
  });
}

export function CreateScreenshotScreen({ go }) {
  const { state, dispatch } = useStore();
  const draft = state.createDraft || {};
  const [preview, setPreview] = useState(draft.screenshot_url || null);
  const [meta, setMeta] = useState(draft.screenshot_meta || null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file) return;
    if (!ACCEPTED.test(file.type)) {
      setError('Поддерживаются JPG, PNG и WEBP');
      return;
    }
    if (file.size > MAX_BYTES) {
      setError('Файл больше 5 МБ');
      return;
    }
    setError(null);
    try {
      const dataUrl = await compressToDataUrl(file);
      setPreview(dataUrl);
      // base64-длина после сжатия — приближённый размер
      setMeta({
        name: file.name,
        size: Math.round((dataUrl.length * 3) / 4),
      });
    } catch (e) {
      setError(e?.message || 'Не удалось обработать изображение');
    }
  };

  const remove = () => {
    setPreview(null);
    setMeta(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleNext = () => {
    haptic('light');
    dispatch({
      type: 'SET_CREATE_DRAFT',
      payload: {
        screenshot_url: preview ?? null,
        screenshot_meta: meta ?? null,
      },
    });
    go('create-preview');
  };

  return (
    <StepShell
      step={5}
      total={6}
      title="Скриншот игрового профиля"
      subtitle="Так другим игрокам будет проще доверять анкете. Шаг необязательный, но рекомендованный"
      onBack={() => go('create-about')}
      footer={
        <button onClick={handleNext} className="btn btn-primary" style={{ width: '100%', height: 54 }}>
          {preview ? 'Продолжить' : 'Пропустить'}
        </button>
      }
    >
      {preview ? (
        <div
          className="glass"
          style={{
            borderRadius: 22,
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.10)',
          }}
        >
          <div style={{ position: 'relative' }}>
            <img
              src={preview}
              alt="screenshot"
              style={{
                width: '100%',
                aspectRatio: '16 / 9',
                objectFit: 'cover',
                display: 'block',
                background: '#000',
              }}
            />
            <button
              onClick={remove}
              style={{
                position: 'absolute',
                top: 10,
                right: 10,
                width: 36,
                height: 36,
                borderRadius: 12,
                background: 'rgba(0,0,0,0.6)',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                cursor: 'pointer',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
              }}
            >
              <Icon name="trash" size={16} />
            </button>
          </div>
          <div
            style={{
              padding: '10px 14px',
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 12,
              color: 'var(--t-2)',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {meta?.name || 'screenshot'}
            </span>
            <span>{formatSize(meta?.size)}</span>
          </div>
        </div>
      ) : (
        <button
          onClick={() => inputRef.current?.click()}
          style={{
            border: '1px dashed rgba(255,255,255,0.20)',
            background: 'rgba(255,255,255,0.03)',
            padding: '32px 20px',
            borderRadius: 22,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 12,
            color: 'var(--t-2)',
            cursor: 'pointer',
            width: '100%',
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: 'rgba(255,255,255,0.06)',
              display: 'grid',
              placeItems: 'center',
            }}
          >
            <Icon name="image" size={26} />
          </div>
          <div style={{ color: '#fff', fontSize: 15, fontWeight: 700 }}>
            Загрузить скриншот
          </div>
          <div style={{ fontSize: 12, color: 'var(--t-3)' }}>
            JPG / PNG / WEBP до 5 МБ
          </div>
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      {error && (
        <div
          style={{
            marginTop: 12,
            padding: '10px 14px',
            borderRadius: 12,
            background: 'rgba(255,59,48,0.12)',
            border: '1px solid rgba(255,59,48,0.30)',
            color: '#FF6961',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {error}
        </div>
      )}
    </StepShell>
  );
}
