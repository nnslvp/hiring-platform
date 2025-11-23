NOTION_STRUCTURE_GUIDE
================================================================================

DATABASE_INFO:
  DATABASE_ID: 27c95810-6f37-8024-b175-d15ffe28f383
  DATA_SOURCE_ID: collection://27c95810-6f37-809d-a172-000b4515d293
  URL: https://www.notion.so/27c958106f378024b175d15ffe28f383
  TOTAL_VACANCIES: 71
  VACANCIES_FILE: vacancies.md

================================================================================

DATABASE_PROPERTIES:
  PROPERTY_NAME: Name
    TYPE: title
    DESCRIPTION: название вакансии

  PROPERTY_NAME: Status
    TYPE: status
    DESCRIPTION: статус вакансии
    VALUES:
      - Заполняется
      - Готово к публикации
      - Опубликовано
      - Закрыто
    WORKFLOW: Заполняется -> Готово к публикации -> Опубликовано -> Закрыто

  PROPERTY_NAME: Мой проект
    TYPE: checkbox
    DESCRIPTION: флаг моего проекта

DATABASE_VIEWS:
  VIEW_NAME: Board view
    TYPE: board
    GROUP_BY: Status

================================================================================

NESTED_DOCUMENTS_STRUCTURE:

  PARENT_PAGE:
    DESCRIPTION: Страница вакансии (родительская страница)
    CONTAINS:
      - Свойства базы данных (Name, Status, Мой проект)
      - Список вложенных страниц
      - Чеклист публикации (Telegram, Viber, Whatsapp, Facebook, Instagram, Threads, TikTok)

  CHILD_PAGE_VACANCY:
    NAME: Вакансия
    DESCRIPTION: Вложенная страница с полным описанием
    CONTAINS:
      - Полное описание вакансии
      - Контактную информацию
      - Условия работы
      - Требования к водителю
      - Информацию об оплате

  CHILD_PAGE_POST:
    NAME: Пост
    DESCRIPTION: Вложенная страница с материалом для публикации
    CONTAINS:
      - Материал для публикации в соцсетях
    NOTE: У большинства вакансий есть страница "Пост", кроме Frysztak

================================================================================

NOTION_HIERARCHY:
  ROOT: Рекрутинг водителей
    CHILD: Вакансии (страница)
      CHILD: Вакансии (база данных)
        CHILD: [Название вакансии] (страница записи)
          CHILD: Вакансия (вложенная страница)
          CHILD: Пост (вложенная страница)

================================================================================

MCP_TOOLS:
  MCP_SERVER: mcp_notionApi_*
  DESCRIPTION: Официальный Notion API для работы с базой данных

  TOOL_GET_DATABASE:
    NAME: mcp_notionApi_API-retrieve-a-database
    PURPOSE: Получение информации о базе данных
    PARAMETERS:
      database_id: 27c95810-6f37-8024-b175-d15ffe28f383
    EXAMPLE:
      mcp_notionApi_API-retrieve-a-database({
        database_id: "27c95810-6f37-8024-b175-d15ffe28f383"
      })

  TOOL_QUERY_DATABASE:
    NAME: mcp_notionApi_API-post-database-query
    PURPOSE: Запрос записей из базы данных
    PARAMETERS:
      database_id: 27c95810-6f37-8024-b175-d15ffe28f383
      page_size: 100 (максимум)
      sorts: [optional] массив объектов сортировки
      filter: [optional] объект фильтрации
    EXAMPLE:
      mcp_notionApi_API-post-database-query({
        database_id: "27c95810-6f37-8024-b175-d15ffe28f383",
        page_size: 100,
        sorts: [{
          property: "Name",
          direction: "ascending"
        }]
      })

  TOOL_GET_PAGE:
    NAME: mcp_notionApi_API-retrieve-a-page
    PURPOSE: Получение информации о странице
    PARAMETERS:
      page_id: ID страницы (можно использовать с дефисами или без)
    EXAMPLE:
      mcp_notionApi_API-retrieve-a-page({
        page_id: "[ID_вакансии]"
      })

  TOOL_GET_BLOCKS:
    NAME: mcp_notionApi_API-get-block-children
    PURPOSE: Получение содержимого страницы (блоки)
    PARAMETERS:
      block_id: ID страницы или блока
      page_size: 100 (максимум)
      start_cursor: [optional] для пагинации
    EXAMPLE:
      mcp_notionApi_API-get-block-children({
        block_id: "[ID_страницы]",
        page_size: 100
      })

  TOOL_SEARCH:
    NAME: mcp_notionApi_API-post-search
    PURPOSE: Поиск в Notion
    PARAMETERS:
      query: строка поиска
      page_size: 100 (максимум)
      filter: [optional] объект фильтрации
    EXAMPLE:
      mcp_notionApi_API-post-search({
        query: "вакансия",
        page_size: 100
      })

  TOOL_UPDATE_PAGE:
    NAME: mcp_notionApi_API-patch-page
    PURPOSE: Обновление свойств страницы
    PARAMETERS:
      page_id: ID страницы
      properties: объект с обновляемыми свойствами
    EXAMPLE:
      mcp_notionApi_API-patch-page({
        page_id: "[ID_страницы]",
        properties: {
          Status: {
            status: {
              name: "Опубликовано"
            }
          }
        }
      })

  TOOL_UPDATE_BLOCK:
    NAME: mcp_notionApi_API-update-a-block
    PURPOSE: Обновление блока
    PARAMETERS:
      block_id: ID блока
      type: тип блока с обновляемыми свойствами
    EXAMPLE:
      mcp_notionApi_API-update-a-block({
        block_id: "[ID_блока]",
        type: {
          paragraph: {
            rich_text: [{
              text: {
                content: "Новый текст"
              }
            }]
          }
        }
      })

  TOOL_APPEND_BLOCKS:
    NAME: mcp_notionApi_API-patch-block-children
    PURPOSE: Добавление блоков к странице
    PARAMETERS:
      block_id: ID страницы или блока
      children: массив блоков для добавления
    EXAMPLE:
      mcp_notionApi_API-patch-block-children({
        block_id: "[ID_страницы]",
        children: [{
          type: "paragraph",
          paragraph: {
            rich_text: [{
              text: {
                content: "Новый блок"
              }
            }]
          }
        }]
      })

================================================================================

IMPORTANT_NOTES:
  ID_FORMAT: Все ID можно использовать с дефисами или без
  PAGINATION: Используйте start_cursor для получения следующих страниц результатов
  RATE_LIMITS: Соблюдайте ограничения API, не делайте слишком много запросов подряд
  STATUS_WORKFLOW: Заполняется -> Готово к публикации -> Опубликовано -> Закрыто
  CHILD_PAGES: Для получения дочерних страниц используйте get-block-children с ID родительской страницы

================================================================================
