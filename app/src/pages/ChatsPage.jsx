import { useEffect, useState } from 'react';
import { webApi } from '../shared/api/client';

export function ChatsPage({ userId }) {
  const [chatsPayload, setChatsPayload] = useState({ items: [], page: 1, total_pages: 1 });
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messagesPayload, setMessagesPayload] = useState(null);
  const [newChatTarget, setNewChatTarget] = useState('');
  const [messageText, setMessageText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadChats = async (page = 1) => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.chats(userId, page, 10);
      setChatsPayload(payload);
    } catch (err) {
      setError(err.message || 'Не удалось загрузить чаты');
    } finally {
      setLoading(false);
    }
  };

  const openChat = async (chatId, page = 1) => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.chatMessages(chatId, userId, page, 10);
      setSelectedChatId(chatId);
      setMessagesPayload(payload);
    } catch (err) {
      setError(err.message || 'Не удалось открыть чат');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelectedChatId(null);
    setMessagesPayload(null);
    loadChats(1);
  }, [userId]);

  const onStartChat = async () => {
    if (!newChatTarget.trim()) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.startChat(userId, newChatTarget.trim());
      setNewChatTarget('');
      await loadChats(1);
      await openChat(payload.chat_id, 1);
    } catch (err) {
      setError(err.message || 'Не удалось создать чат');
    } finally {
      setLoading(false);
    }
  };

  const onSend = async () => {
    if (!selectedChatId || !messageText.trim()) return;
    setLoading(true);
    setError('');
    try {
      await webApi.sendChatMessage(selectedChatId, userId, messageText.trim());
      setMessageText('');
      await openChat(selectedChatId, 1);
      await loadChats(1);
    } catch (err) {
      setError(err.message || 'Не удалось отправить сообщение');
    } finally {
      setLoading(false);
    }
  };

  const onDeleteChat = async () => {
    if (!selectedChatId) return;
    if (!window.confirm('Удалить чат полностью?')) return;
    setLoading(true);
    setError('');
    try {
      await webApi.deleteChat(selectedChatId, userId);
      setSelectedChatId(null);
      setMessagesPayload(null);
      await loadChats(1);
    } catch (err) {
      setError(err.message || 'Не удалось удалить чат');
    } finally {
      setLoading(false);
    }
  };

  if (!userId) return <p>Введите user_id сверху, чтобы открыть чаты.</p>;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Чаты</h2>
        <button onClick={() => loadChats(chatsPayload.page || 1)} disabled={loading}>Обновить</button>
      </div>

      <div className="form-inline">
        <input
          placeholder="Никнейм или @username"
          value={newChatTarget}
          onChange={(e) => setNewChatTarget(e.target.value)}
        />
        <button onClick={onStartChat} disabled={loading}>Начать новый чат</button>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p>Загрузка...</p>}

      <div className="grid two split">
        <div>
          <h3>Ваши чаты</h3>
          <div className="list-buttons">
            {(chatsPayload.items || []).map((chat) => (
              <button
                key={chat.chat_id}
                className={selectedChatId === chat.chat_id ? 'active' : ''}
                onClick={() => openChat(chat.chat_id, 1)}
              >
                {(chat.unread_count || 0) > 0 ? '🔴 ' : ''}
                {chat.full_name || chat.username || `chat_${chat.chat_id}`}
              </button>
            ))}
          </div>
          <div className="menu-row">
            <button
              disabled={(chatsPayload.page || 1) <= 1}
              onClick={() => loadChats((chatsPayload.page || 1) - 1)}
            >
              {'<'}
            </button>
            <span>Стр. {chatsPayload.page || 1}/{chatsPayload.total_pages || 1}</span>
            <button
              disabled={(chatsPayload.page || 1) >= (chatsPayload.total_pages || 1)}
              onClick={() => loadChats((chatsPayload.page || 1) + 1)}
            >
              {'>'}
            </button>
          </div>
        </div>

        <div>
          <h3>Переписка</h3>
          {!messagesPayload && <p>Выберите чат слева.</p>}
          {messagesPayload && (
            <>
              <p><b>Собеседник:</b> {messagesPayload.counterpart?.full_name || messagesPayload.counterpart?.username || messagesPayload.counterpart?.id}</p>
              <div className="messages">
                {(messagesPayload.items || []).map((message) => (
                  <div key={message.id} className={message.from_user_id === userId ? 'msg own' : 'msg'}>
                    <b>{message.from_user_id === userId ? 'Вы' : 'Собеседник'}</b>
                    <p>{message.text}</p>
                  </div>
                ))}
              </div>
              <div className="menu-row">
                <button
                  disabled={!messagesPayload.has_older}
                  onClick={() => openChat(selectedChatId, (messagesPayload.page || 1) + 1)}
                >
                  Дальше {'>'}
                </button>
                <button
                  disabled={!messagesPayload.has_newer}
                  onClick={() => openChat(selectedChatId, (messagesPayload.page || 1) - 1)}
                >
                  {'<'} Назад
                </button>
              </div>
              <div className="form-inline">
                <input
                  placeholder="Введите текст сообщения"
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                />
                <button onClick={onSend} disabled={loading}>Отправить</button>
                <button className="danger" onClick={onDeleteChat} disabled={loading}>Удалить чат</button>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
