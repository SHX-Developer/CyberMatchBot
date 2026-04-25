import { useState } from 'react';
import { Icon } from '../../components/Icon.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { deleteMe } from '../../api.js';
import { useStore } from '../../store.jsx';
import { closeApp, haptic, showAlert, showPopup } from '../../telegram.js';

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      style={{
        width: 46,
        height: 28,
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.12)',
        background: checked
          ? 'linear-gradient(135deg, var(--accent), var(--accent-2))'
          : 'rgba(255,255,255,0.06)',
        position: 'relative',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'background 0.2s',
        flexShrink: 0,
        boxShadow: checked ? '0 0 12px var(--accent-glow)' : 'none',
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 2,
          left: checked ? 20 : 2,
          width: 22,
          height: 22,
          borderRadius: '50%',
          background: '#fff',
          transition: 'left 0.2s ease',
          boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
        }}
      />
    </button>
  );
}

function Row({ icon, label, sub, right, onClick, danger }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 10px',
        borderRadius: 14,
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: danger
            ? 'rgba(255,59,48,0.10)'
            : 'rgba(255,255,255,0.06)',
          border: `1px solid ${danger ? 'rgba(255,59,48,0.30)' : 'rgba(255,255,255,0.10)'}`,
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          color: danger ? '#FF6961' : '#fff',
        }}
      >
        <Icon name={icon} size={16} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: danger ? '#FF6961' : '#fff' }}>{label}</div>
        {sub && <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 1 }}>{sub}</div>}
      </div>
      {right}
    </div>
  );
}

export function SecurityScreen({ go }) {
  const { dispatch } = useStore();
  const [showActivity, setShowActivity] = useState(true);
  const [notifyLikes, setNotifyLikes] = useState(true);
  const [notifyMessages, setNotifyMessages] = useState(true);

  const handleDelete = async () => {
    const choice = await showPopup({
      title: 'Удалить аккаунт?',
      message: 'Это действие нельзя отменить. Все ваши анкеты, лайки и чаты будут удалены.',
      buttons: [
        { id: 'cancel', type: 'cancel' },
        { id: 'delete', type: 'destructive', text: 'Удалить' },
      ],
    });
    if (choice !== 'delete') return;
    haptic('warning');
    try {
      await deleteMe();
      dispatch({ type: 'CLEAR_USER' });
      showAlert('Аккаунт удалён');
      closeApp();
    } catch (e) {
      showAlert('Не удалось удалить аккаунт');
    }
  };

  return (
    <StepShell
      title="Безопасность"
      subtitle="Приватность, уведомления, удаление аккаунта"
      onBack={() => go('profile')}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="glass" style={{ borderRadius: 22, padding: 6 }}>
          <Row
            icon="bolt"
            label="Показывать активность"
            sub="Другие увидят, когда вы были в сети"
            right={<Toggle checked={showActivity} onChange={setShowActivity} />}
          />
          <div style={{ height: 1, background: 'rgba(255,255,255,0.06)' }} />
          <Row
            icon="heart"
            label="Уведомления о лайках"
            right={<Toggle checked={notifyLikes} onChange={setNotifyLikes} />}
          />
          <div style={{ height: 1, background: 'rgba(255,255,255,0.06)' }} />
          <Row
            icon="chat"
            label="Уведомления о сообщениях"
            right={<Toggle checked={notifyMessages} onChange={setNotifyMessages} />}
          />
        </div>

        <div className="glass" style={{ borderRadius: 22, padding: 6 }}>
          <Row
            icon="shield"
            label="Заблокированные пользователи"
            sub="Никто не заблокирован"
            right={<Icon name="caret-right" size={16} stroke="var(--t-2)" />}
          />
        </div>

        <div className="glass" style={{ borderRadius: 22, padding: 6 }}>
          <Row
            icon="trash"
            label="Удалить аккаунт"
            sub="Стирает все анкеты, лайки и чаты"
            danger
            onClick={handleDelete}
            right={<Icon name="caret-right" size={16} stroke="rgba(255,105,97,0.7)" />}
          />
        </div>

        <div
          style={{
            fontSize: 11,
            color: 'var(--t-3)',
            lineHeight: 1.5,
            padding: '8px 4px',
            textAlign: 'center',
          }}
        >
          Уведомления и видимость активности — заглушка для MVP. Включение/удаление аккаунта работает.
        </div>
      </div>
    </StepShell>
  );
}
