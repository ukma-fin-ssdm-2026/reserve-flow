1. Ключові функції, які покриває модель:

    1) Реєстрація, авторизація та управління ролями (Клієнт, Постачальник, Адміністратор).

    2) Ведення довідника приміщень адміністратором та постачальниками за дозволу адміністратора (додавання кімнат, налаштування місткості та атрибутів).

    3) Пошук та фільтрація доступних кімнат і часових слотів.

    4) Створення, підтвердження та скасування бронювань із запобіганням подвійному резервуванню.

    5) Керування статусом окремих часових слотів постачальником (доступний/недоступний).

    6) Планування та відправка автоматичних сповіщень (Email-нагадування).

    7) Ведення системного журналу аудиту (логування дій користувачів для модерації).

2. Сутності, атрибути та ключі:

    User (Користувач)

        id: UUID (PK)

        email: String (Unique) — <<чутливі дані / зашифровано>>

        full_name: String — <<персональні дані / зашифровано>>

        password_hash: String — <<чутливі дані>>

        role: Enum (Client, Provider, Admin) — <<чутливі дані>>

        notifications_enabled: Boolean

        is_blocked: Boolean

    Room (Приміщення)

        id: UUID (PK)

        provider_id: UUID (FK -> User.id)

        name_ua: String

        name_en: String

        capacity: Integer

        has_projector: Boolean

        is_shelter: Boolean

        building_ua: Enum ("Корпус 1", "Корпус 2", "Корпус 3", "Корпус 4", "Корпус 5",
        "Корпус 6", "Корпус 7", "Корпус 8", "Корпус 9", "Корпус 10", "КМЦ", "Наукова бібліотека", "Історико-музейний комплекс НаУКМА")

        building_en: Enum ("Building 1", "Building 2", "Building 3", "Building 4", "Building 5", "Building 6", "Building 7", "Building 8", "Building 9", "Building 10", "Cultural and Art Center (KMC)", "Research Library", "Historical and Museum Complex of NaUKMA")

        room_number : String

        moderation_status: Enum (Pending, Approved, Rejected)

        approved_by: UUID (FK -> User.id, Nullable)

    TimeSlot (Часовий слот)

        id: UUID (PK)

        room_id: UUID (FK -> Room.id)

        start_time: Timestamp

        end_time: Timestamp

        is_available: Boolean (контролюється постачальником)

        closure_reason: String (Nullable)

    Booking (Бронювання)

        id: UUID (PK)

        client_id: UUID (FK -> User.id)

        slot_id: UUID (FK -> TimeSlot.id)

        status: Enum (Pending, Confirmed, Cancelled, Rejected)

        rejection_reason: String (Nullable) — обов'язкове лише для status = Rejected (FR-010)

        created_at: Timestamp

    Notification (Сповіщення)

        id: UUID (PK)

        booking_id: UUID (FK -> Booking.id)

        scheduled_time: Timestamp

        status: Enum (Pending, Sent, Failed)

        retry_count: Integer

    AuditLog (Журнал аудиту)

        id: UUID (PK)

        actor_type: Enum (User, System) — хто виконав дію: користувач чи системний процес (Notification Scheduler)

        user_id: UUID (FK -> User.id, Nullable) — <<персональні дані>>; порожнє, якщо actor_type = System

        action: Enum (BookingCreated, BookingCancelled, BookingConfirmed, BookingRejected, SlotStatusChanged, RoomRequestSubmitted, RoomApproved, RoomRejected, UserBlocked, UserUnblocked, NotificationFailed)

        entity_type: Enum (User, Room, TimeSlot, Booking, Notification)

        entity_id: UUID — ідентифікатор об'єкта дії (без FK, бо тип об'єкта різний)

        details: String (Nullable) — причина або текст помилки; без персональних даних

        timestamp: Timestamp

        Інваріанти:
        - actor_type = User  ⇔  user_id заповнене;
        - записи лише додаються, не змінюються й не видаляються (захист від Repudiation, threat-model.md).

3. Зв'язки та кардинальність:

    User ||--o{ Room (через provider_id): Один постачальник або адміністратор може створювати та володіти багатьма приміщеннями; кожне приміщення закріплене за одним відповідальним користувачем (адміністратор, якщо постачальника ще не знайдено).

    User ||--o{ Room (через approved_by): Один адміністратор може розглядати та погоджувати/відхиляти запити на публікацію багатьох приміщень; для кожного приміщення фіксується адміністратор, який провів модерацію (або значення відсутнє, якщо приміщення ще на розгляді).

    Room ||--o{ TimeSlot: Одне приміщення має багато часових слотів, слот належить одному приміщенню.

    User (Client) ||--o{ Booking: Один клієнт може мати багато бронювань, бронювання належить одному клієнту.

    TimeSlot ||--o{ Booking: Один часовий слот може мати історію бронювань (наприклад, скасовані та одне активне), бронювання стосується одного слота.

    Booking ||--o| Notification: Одне бронювання може мати одне заплановане сповіщення.

    User |o--o{ AuditLog: Один користувач може згенерувати багато записів аудиту; запис належить щонайбільше одному користувачу (для дій системи user_id порожнє).

Використання ШІ: у структуруванні документа та при додатковій перевірці відповідності стандартам завдання було використано ШІ Gemini (відповідно до ідей команди). Документ було перевірено, доповнено, відредаговано та затверджено учасниками команди.
