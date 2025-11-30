import { chromium } from 'playwright-extra';
import stealth from 'puppeteer-extra-plugin-stealth';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';

chromium.use(stealth());

const OUTPUT_DIR = './exported_messages';
const STATE_FILE = './export_state.json';
const BROWSER_INFO_FILE = './browser_info.json';
const CDP_PORT = 9222;

let globalBrowser = null;
let globalContext = null;
let isExistingBrowserGlobal = false;

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function randomDelay(min = 500, max = 1000) {
  const ms = Math.floor(Math.random() * (max - min + 1)) + min;
  await delay(ms);
}

function loadState() {
  if (fs.existsSync(STATE_FILE)) {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
  }
  return { chats: {} };
}

function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

async function checkBrowserRunning() {
  try {
    const response = await fetch(`http://localhost:${CDP_PORT}/json/version`);
    if (response.ok) {
      return true;
    }
  } catch (e) {
    return false;
  }
  return false;
}

function saveBrowserInfo(cdpUrl) {
  fs.writeFileSync(BROWSER_INFO_FILE, JSON.stringify({ cdpUrl, port: CDP_PORT }, null, 2));
}

function loadBrowserInfo() {
  if (fs.existsSync(BROWSER_INFO_FILE)) {
    return JSON.parse(fs.readFileSync(BROWSER_INFO_FILE, 'utf-8'));
  }
  return null;
}

function clearBrowserInfo() {
  if (fs.existsSync(BROWSER_INFO_FILE)) {
    fs.unlinkSync(BROWSER_INFO_FILE);
  }
}

async function launchDetachedBrowser() {
  const executablePath = chromium.executablePath();
  
  const chromeArgs = [
    `--remote-debugging-port=${CDP_PORT}`,
    '--no-first-run',
    '--no-default-browser-check',
    `--user-data-dir=${path.join(process.cwd(), '.chrome-data')}`
  ];
  
  const chromeProcess = spawn(executablePath, chromeArgs, {
    detached: true,
    stdio: 'ignore'
  });
  
  chromeProcess.unref();
  
  await delay(2000);
  
  saveBrowserInfo(`http://localhost:${CDP_PORT}`);
}

async function createStealthContext(browser) {
  const contextOptions = {
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  };

  const context = await browser.newContext(contextOptions);
  return context;
}

async function login(page) {
  console.log('\n========================================');
  console.log('Требуется вход в аккаунт');
  console.log('Выполните вход вручную в открывшемся браузере');
  console.log('После успешного входа нажмите Enter в терминале');
  console.log('========================================\n');

  await page.goto('https://www.tiktok.com/login');

  await new Promise(resolve => {
    process.stdin.once('data', () => resolve());
  });

  console.log('✓ Вход выполнен успешно (данные сохранены в user-data-dir)');
}

async function scrollToLoadAllChats(page) {
  console.log('Прокрутка списка чатов для загрузки всех...');
  
  let previousCount = 0;
  let unchangedCount = 0;
  const maxUnchanged = 3;

  while (unchangedCount < maxUnchanged) {
    const currentCount = await page.evaluate(() => {
      return document.querySelectorAll('[data-e2e="chat-list-item"]').length;
    });

    await page.evaluate(() => {
      const chatListContainer = document.querySelector('[class*="ChatList"]') ||
                                document.querySelector('[class*="conversation-list"]') ||
                                document.querySelector('[data-e2e="chat-list"]') ||
                                document.querySelector('div[class*="list-container"]');
      if (chatListContainer) {
        chatListContainer.scrollTop = chatListContainer.scrollHeight;
      }
    });

    await randomDelay(1000, 1500);

    if (currentCount === previousCount) {
      unchangedCount++;
    } else {
      unchangedCount = 0;
      console.log(`  Загружено чатов: ${currentCount}`);
    }

    previousCount = currentCount;
  }
  
  console.log(`✓ Загрузка списка завершена. Всего чатов: ${previousCount}`);
  return previousCount;
}

async function scrollToLoadMessages(page) {
  console.log('  Загрузка истории сообщений...');
  
  let previousHeight = 0;
  let unchangedCount = 0;
  const maxUnchanged = 2;

  while (unchangedCount < maxUnchanged) {
    await page.evaluate(() => {
      const container = document.querySelector('[class*="ChatBox"]') ||
                       document.querySelector('[class*="MessageList"]') || 
                       document.querySelector('[class*="message-list"]') ||
                       document.querySelector('[class*="message-container"]') ||
                       document.querySelector('div[class*="DM"]');
      if (container) {
        container.scrollTop = 0;
      }
    });

    await randomDelay(800, 1200);

    const currentHeight = await page.evaluate(() => {
      const container = document.querySelector('[class*="ChatBox"]') ||
                       document.querySelector('[class*="MessageList"]') || 
                       document.querySelector('[class*="message-list"]') ||
                       document.querySelector('[class*="message-container"]') ||
                       document.querySelector('div[class*="DM"]');
      return container ? container.scrollHeight : 0;
    });

    if (currentHeight === previousHeight) {
      unchangedCount++;
    } else {
      unchangedCount = 0;
    }

    previousHeight = currentHeight;
  }
}

function getMessageHash(message) {
  return `${message.text}_${message.time}_${message.author}`.replace(/\s/g, '');
}

async function exportMessages(page, state) {
  console.log('\nПереход к сообщениям...');
  await page.goto('https://www.tiktok.com/messages?scene=business', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await randomDelay(3000, 4000);

  console.log('Загрузка списка чатов...');
  
  try {
    await page.waitForSelector('[data-e2e="chat-list-item"]', { timeout: 60000 });
  } catch (e) {
    console.error('Не удалось найти список чатов. Возможно TikTok заблокировал доступ или изменил структуру страницы.');
    
    console.log('\nDEBUG: Дополнительная информация:');
    const pageUrl = page.url();
    console.log(`Текущий URL: ${pageUrl}`);
    
    const hasLoginElements = await page.evaluate(() => {
      return {
        hasLoginButton: document.querySelector('[class*="login"]') !== null,
        hasLoginForm: document.querySelector('form') !== null,
        hasDataE2E: document.querySelector('[data-e2e="chat-list-item"]') !== null,
        bodyText: document.body.textContent.substring(0, 500)
      };
    });
    console.log('Элементы страницы:', hasLoginElements);
    
    return;
  }
  
  await randomDelay(500, 800);

  await scrollToLoadAllChats(page);

  const chatList = await page.$$('[data-e2e="chat-list-item"]');
  console.log(`\nГотово к обработке чатов: ${chatList.length}`);
  
  if (chatList.length === 0) {
    console.log('\nDEBUG: Не найдено ни одного чата. Дополнительная диагностика:');
    const debugInfo = await page.evaluate(() => {
      const e2eElements = document.querySelectorAll('[data-e2e]');
      const e2eAttrs = Array.from(e2eElements).map(el => el.getAttribute('data-e2e')).slice(0, 10);
      return {
        allDataE2EAttributes: e2eAttrs,
        bodyClasses: document.body.className,
        hasMessages: document.querySelector('[class*="Message"]') !== null
      };
    });
    console.log('DEBUG информация:', debugInfo);
    return;
  }

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const exportSummary = [];
  let newMessagesTotal = 0;
  let skippedUnreadChats = 0;

  for (let i = 0; i < chatList.length; i++) {
    console.log(`\n[${i + 1}/${chatList.length}] Обработка чата...`);
    
    const chatItems = await page.$$('[data-e2e="chat-list-item"]');
    
    if (i >= chatItems.length) {
      console.log('  Чат недоступен, пропускаем');
      continue;
    }

    const chatInfo = await chatItems[i].evaluate((element, index) => {
      const nameElement = element.querySelector('[class*="InfoNickname"]') ||
                         element.querySelector('[class*="PInfoNickname"]') ||
                         element.querySelector('[data-e2e*="username"]') ||
                         element.querySelector('[class*="username"]');
      
      const chatName = nameElement ? nameElement.textContent.trim() : `Chat_${Date.now()}`;
      
      const lastMessagePreview = element.querySelector('[class*="SpanInfoExtract"]');
      const lastMessageTime = element.querySelector('[class*="SpanInfoTime"]');
      
      const unreadBadge = element.querySelector('[class*="SpanNewMessage"]') ||
                         element.querySelector('[class*="NewMessage"]');
      const isUnread = unreadBadge !== null;
      const unreadCount = unreadBadge ? unreadBadge.textContent.trim() : null;
      
      return {
        chatName,
        foundBySelector: nameElement ? nameElement.className : 'not_found',
        lastMessagePreview: lastMessagePreview ? lastMessagePreview.textContent.trim() : null,
        lastMessageTime: lastMessageTime ? lastMessageTime.textContent.trim() : null,
        isUnread,
        unreadCount
      };
    }, i);

    const chatName = chatInfo.chatName;
    const chatKey = chatName.replace(/[^a-zA-Z0-9а-яА-Я]/g, '_');
    
    console.log(`  Чат: ${chatName}`);
    if (chatInfo.lastMessageTime) {
      console.log(`  Время последнего сообщения: ${chatInfo.lastMessageTime}`);
    }
    
    if (i === 0) {
      console.log(`  DEBUG: Селектор найден через класс: ${chatInfo.foundBySelector}`);
    }

    if (chatInfo.isUnread) {
      console.log(`  ⏭️  Пропуск: ${chatInfo.unreadCount} непрочитанных сообщений (сохраняем индикацию)`);
      skippedUnreadChats++;
      continue;
    }

    if (chatInfo.lastMessageTime && state.chats[chatKey]?.lastExport) {
      try {
        const lastExportDate = new Date(state.chats[chatKey].lastExport);
        let lastMessageDate;

        if (chatInfo.lastMessageTime.includes(':') && !chatInfo.lastMessageTime.includes('/')) {
          const today = new Date();
          const [hours, minutes] = chatInfo.lastMessageTime.split(':');
          lastMessageDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 
                                    parseInt(hours), parseInt(minutes));
          
          if (lastMessageDate > today) {
            lastMessageDate.setDate(lastMessageDate.getDate() - 1);
          }
        } else {
          lastMessageDate = new Date(chatInfo.lastMessageTime);
        }

        if (lastMessageDate <= lastExportDate) {
          console.log(`  ⏭️  Пропуск: последнее сообщение (${chatInfo.lastMessageTime}) старше последнего экспорта`);
          continue;
        } else {
          console.log(`  ✓ Есть новые сообщения после ${lastExportDate.toLocaleString('ru-RU')}`);
        }
      } catch (e) {
        console.log(`  ⚠️  Не удалось распарсить время, открываем чат`);
      }
    }

    await chatItems[i].click();
    await randomDelay(1000, 1500);

    const chatUsername = await page.evaluate(() => {
      const headerLink = document.querySelector('#main-content-messages > div:nth-child(2) > div:nth-child(1) > div > a');
      if (headerLink) {
        const href = headerLink.getAttribute('href');
        if (href && href.startsWith('/@')) {
          return href.replace('/@', '');
        }
      }
      return null;
    });

    const finalChatName = chatUsername || chatName;
    const finalChatKey = finalChatName.replace(/[^a-zA-Z0-9а-яА-Я_]/g, '_');
    
    if (chatUsername) {
      console.log(`  Username: @${chatUsername}`);
    }

    await scrollToLoadMessages(page);

    const messages = await page.evaluate(() => {
      const chatItems = document.querySelectorAll('[data-e2e="chat-item"]');
      const result = [];

      chatItems.forEach(item => {
        const hasVideo = item.querySelector('[class*="VideoContainer"]');
        const hasImage = item.querySelector('[class*="ImageContainer"]');
        
        if (hasVideo || hasImage) {
          return;
        }

        const textContainer = item.querySelector('[class*="TextContainer"]');
        if (!textContainer) {
          return;
        }

        const textElement = textContainer.querySelector('[class*="PText"]') || 
                           textContainer.querySelector('p');
        
        if (!textElement) {
          return;
        }

        const text = textElement.textContent.trim();
        
        if (text) {
          const avatar = item.querySelector('[data-e2e="chat-avatar"]');
          const authorLink = avatar ? avatar.closest('a') : null;
          const author = authorLink ? authorLink.getAttribute('href').replace('/@', '') : 'Unknown';
          
          const timeContainer = item.closest('[class*="ChatItemWrapper"]')?.previousElementSibling;
          const timeElement = timeContainer?.querySelector('[class*="TimeContainer"] span');
          const time = timeElement ? timeElement.textContent.trim() : '';

          result.push({
            text,
            time,
            author,
            timestamp: Date.now()
          });
        }
      });

      return result;
    });

    const existingHashes = new Set(state.chats[finalChatKey]?.messageHashes || []);
    
    const newMessages = messages.filter(msg => {
      const hash = getMessageHash(msg);
      return !existingHashes.has(hash);
    });

    if (newMessages.length > 0) {
      const allMessages = [...messages];
      const allHashes = allMessages.map(getMessageHash);

      const chatData = {
        chatName: finalChatName,
        displayName: chatName,
        lastExportDate: new Date().toISOString(),
        messagesCount: allMessages.length,
        messages: allMessages
      };

      const fileName = `${finalChatKey}.json`;
      const filePath = path.join(OUTPUT_DIR, fileName);
      fs.writeFileSync(filePath, JSON.stringify(chatData, null, 2));

      state.chats[finalChatKey] = {
        chatName: finalChatName,
        displayName: chatName,
        lastExport: new Date().toISOString(),
        messageHashes: allHashes,
        messagesCount: allMessages.length
      };

      newMessagesTotal += newMessages.length;
      console.log(`  ✓ Новых сообщений: ${newMessages.length} (всего в чате: ${allMessages.length})`);
      
      exportSummary.push({
        chatName: finalChatName,
        displayName: chatName,
        fileName,
        newMessages: newMessages.length,
        totalMessages: allMessages.length
      });
    } else {
      console.log(`  ✓ Новых сообщений нет`);
    }

    await randomDelay(500, 1000);
  }

  saveState(state);

  const summaryPath = path.join(OUTPUT_DIR, 'export_summary.json');
  fs.writeFileSync(summaryPath, JSON.stringify({
    exportDate: new Date().toISOString(),
    totalChats: chatList.length,
    skippedUnreadChats,
    chatsWithNewMessages: exportSummary.length,
    newMessagesTotal,
    chats: exportSummary
  }, null, 2));

  console.log('\n========================================');
  console.log('✓ Экспорт завершен!');
  console.log(`✓ Всего чатов: ${chatList.length}`);
  console.log(`✓ Пропущено непрочитанных: ${skippedUnreadChats}`);
  console.log(`✓ Чатов с новыми сообщениями: ${exportSummary.length}`);
  console.log(`✓ Новых сообщений: ${newMessagesTotal}`);
  console.log(`✓ Файлы сохранены в: ${OUTPUT_DIR}`);
  console.log('========================================\n');
}

async function main() {
  const state = loadState();
  const userDataDir = path.join(process.cwd(), '.chrome-data');
  const isFirstRun = !fs.existsSync(userDataDir);

  if (isFirstRun) {
    console.log('\n========================================');
    console.log('Первый запуск - требуется вход в аккаунт');
    console.log('========================================\n');
  } else {
    console.log('\n========================================');
    console.log('Экспорт сообщений (сессия сохранена в браузере)');
    console.log('========================================\n');
  }

  let browser;
  let isExistingBrowser = false;

  const browserRunning = await checkBrowserRunning();
  
  if (browserRunning) {
    try {
      console.log('✓ Найден запущенный браузер, подключаюсь...');
      browser = await chromium.connectOverCDP(`http://localhost:${CDP_PORT}`);
      isExistingBrowser = true;
      console.log('✓ Подключен к существующему браузеру');
    } catch (e) {
      console.log('Не удалось подключиться к браузеру, запускаю новый...');
      clearBrowserInfo();
    }
  }

  if (!browser) {
    console.log('Запуск нового браузера как независимого процесса...');
    await launchDetachedBrowser();
    
    browser = await chromium.connectOverCDP(`http://localhost:${CDP_PORT}`);
    isExistingBrowser = true;
    
    console.log('✓ Браузер запущен в независимом режиме');
  }

  globalBrowser = browser;
  isExistingBrowserGlobal = isExistingBrowser;

  const context = browser.contexts()[0] || await createStealthContext(browser);
  globalContext = context;
  
  const page = context.pages()[0] || await context.newPage();

  if (isFirstRun) {
    await login(page);
  } else {
    console.log('Проверка сессии...');
    await page.goto('https://www.tiktok.com/messages?scene=business', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await randomDelay(3000, 4000);

    const needsLogin = await page.evaluate(() => {
      return window.location.href.includes('login') || 
             document.querySelector('[class*="login"]') !== null;
    });

    if (needsLogin) {
      console.log('Сессия истекла, требуется повторный вход');
      await login(page);
    } else {
      console.log('✓ Сессия активна (данные из user-data-dir)');
    }
  }

  await exportMessages(page, state);
  
  console.log('\n========================================');
  console.log('Браузер остается открытым для следующего запуска');
  console.log('Данные сессии сохранены в: .chrome-data/');
  console.log('========================================\n');
}

async function gracefulShutdown(signal) {
  console.log(`\n\nПолучен сигнал завершения (${signal})`);
  
  try {
    if (globalBrowser && isExistingBrowserGlobal) {
      console.log('✓ Отсоединение от существующего браузера');
    } else if (globalBrowser) {
      console.log('✓ Браузер останется открытым с CDP на порту ' + CDP_PORT);
    }
    console.log('✓ Все данные сохранены в .chrome-data/');
  } catch (e) {
    console.log('Ошибка при завершении:', e.message);
  }
  
  console.log('✓ Скрипт завершен. Браузер продолжает работать.');
  process.exit(0);
}

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

main().catch(console.error);
