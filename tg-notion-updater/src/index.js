/**
 * TikTok Notion Updater Bot
 * Cloudflare Worker для обновления статусов в Notion через Telegram
 */

export default {
  async fetch(request, env) {
    // Только POST запросы от Telegram webhook
    if (request.method !== 'POST') {
      return new Response('OK', { status: 200 });
    }

    try {
      const update = await request.json();
      
      // Проверяем наличие сообщения
      if (!update.message?.text) {
        return new Response('OK', { status: 200 });
      }

      const chatId = update.message.chat.id;
      const text = update.message.text;

      // Извлекаем username из TikTok ссылки
      const username = extractTikTokUsername(text);
      
      if (!username) {
        await sendTelegramMessage(env.TG_BOT_TOKEN, chatId, 
          '⚠️ Не удалось извлечь username из ссылки.\n\nОтправьте ссылку в формате:\n• tiktok.com/@username\n• vm.tiktok.com/...');
        return new Response('OK', { status: 200 });
      }

      // Ищем запись в Notion
      const page = await findNotionPage(env, username);
      
      if (!page) {
        const newPage = await createNotionPage(env, username);
        if (newPage) {
          await sendTelegramMessage(env.TG_BOT_TOKEN, chatId,
            `✅ Создана новая запись "${username}"!\n\nСтатус: "${env.STATUS_TO}"\n\nВот запись:\n${newPage.url}`);
        } else {
          await sendTelegramMessage(env.TG_BOT_TOKEN, chatId,
            `❌ Ошибка при создании записи для "${username}".`);
        }
        return new Response('OK', { status: 200 });
      }

      // Проверяем текущий статус (FSM-логика)
      const currentStatus = page.properties[env.COL_STATUS]?.status?.name;
      
      if (currentStatus !== env.STATUS_FROM) {
        // Специальное сообщение, если водитель уже был перенесён
        if (currentStatus === env.STATUS_TO) {
          await sendTelegramMessage(env.TG_BOT_TOKEN, chatId,
            `ℹ️ Водитель "${username}" уже был добавлен ранее.\n\nСтатус: "${currentStatus}"\n\nВот запись:\n${page.url}`);
        } else {
          await sendTelegramMessage(env.TG_BOT_TOKEN, chatId,
            `⛔️ Не могу обновить.\n\nЗапись в статусе "${currentStatus}", а нужен "${env.STATUS_FROM}".\n\nИзменения отклонены.\n\nВот запись:\n${page.url}`);
        }
        return new Response('OK', { status: 200 });
      }

      // Обновляем статус
      const updatedPage = await updateNotionPage(env, page.id);
      
      if (updatedPage) {
        await sendTelegramMessage(env.TG_BOT_TOKEN, chatId,
          `✅ Статус обновлен на "${env.STATUS_TO}"!\n\nВот запись:\n${updatedPage.url}`);
      } else {
        await sendTelegramMessage(env.TG_BOT_TOKEN, chatId,
          '❌ Ошибка при обновлении записи в Notion.');
      }

      return new Response('OK', { status: 200 });

    } catch (error) {
      console.error('Error:', error);
      return new Response('OK', { status: 200 });
    }
  }
};

/**
 * Извлекает username из TikTok ссылки
 * Поддерживает форматы:
 * - https://www.tiktok.com/@username
 * - https://tiktok.com/@username
 * - tiktok.com/@username
 * - https://vm.tiktok.com/XXXXXXX/ (короткие ссылки - только извлечение, редирект не обрабатывается)
 */
function extractTikTokUsername(text) {
  if (!text) return null;
  
  // Паттерн для стандартных ссылок: tiktok.com/@username
  const standardMatch = text.match(/tiktok\.com\/@([a-zA-Z0-9_.]+)/i);
  if (standardMatch) {
    return standardMatch[1];
  }
  
  // Паттерн для прямого ввода username (без ссылки)
  // Если текст выглядит как username (без пробелов и спецсимволов)
  const directMatch = text.trim().match(/^@?([a-zA-Z0-9_.]+)$/);
  if (directMatch) {
    return directMatch[1];
  }
  
  return null;
}

/**
 * Поиск страницы в Notion по username (поле Name)
 */
async function findNotionPage(env, username) {
  const response = await fetch(`https://api.notion.com/v1/databases/${env.NOTION_DB_ID}/query`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.NOTION_SECRET}`,
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      filter: {
        property: env.COL_SEARCH,
        title: {
          equals: username
        }
      },
      page_size: 1
    })
  });

  if (!response.ok) {
    console.error('Notion search error:', await response.text());
    return null;
  }

  const data = await response.json();
  return data.results?.[0] || null;
}

/**
 * Обновление статуса страницы в Notion
 */
async function updateNotionPage(env, pageId) {
  const response = await fetch(`https://api.notion.com/v1/pages/${pageId}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${env.NOTION_SECRET}`,
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      properties: {
        [env.COL_STATUS]: {
          status: {
            name: env.STATUS_TO
          }
        }
      }
    })
  });

  if (!response.ok) {
    console.error('Notion update error:', await response.text());
    return null;
  }

  return await response.json();
}

/**
 * Создание новой страницы водителя в Notion
 */
async function createNotionPage(env, username) {
  const tiktokUrl = `https://www.tiktok.com/@${username}`;
  
  const response = await fetch('https://api.notion.com/v1/pages', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.NOTION_SECRET}`,
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      parent: { database_id: env.NOTION_DB_ID },
      properties: {
        [env.COL_SEARCH]: {
          title: [{ text: { content: username } }]
        },
        'TikTok URL': {
          url: tiktokUrl
        },
        [env.COL_STATUS]: {
          status: { name: env.STATUS_TO }
        }
      }
    })
  });

  if (!response.ok) {
    console.error('Notion create error:', await response.text());
    return null;
  }

  return await response.json();
}

/**
 * Отправка сообщения в Telegram
 */
async function sendTelegramMessage(token, chatId, text) {
  const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: 'HTML',
      disable_web_page_preview: true
    })
  });

  if (!response.ok) {
    console.error('Telegram error:', await response.text());
  }

  return response.ok;
}

