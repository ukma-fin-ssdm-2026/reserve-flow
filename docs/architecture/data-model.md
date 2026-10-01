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

        building_en: building_en: Enum ("Building 1", "Building 2", "Building 3", "Building 4", "Building 5", "Building 6", "Building 7", "Building 8", "Building 9", "Building 10", "Cultural and Art Center (KMC)", "Research Library", "Historical and Museum Complex of NaUKMA")

        room_number : String

        is_approved: Boolean (статус модерації адміном)

    TimeSlot (Часовий слот)

        id: UUID (PK)

        room_id: UUID (FK -> Room.id)

        start_time: Timestamp

        end_time: Timestamp

        is_available: Boolean (контролюється постачальником)

    Booking (Бронювання)

        id: UUID (PK)

        client_id: UUID (FK -> User.id)

        slot_id: UUID (FK -> TimeSlot.id)

        status: Enum (Pending, Confirmed, Cancelled, Rejected)

        created_at: Timestamp

    Notification (Сповіщення)

        id: UUID (PK)

        booking_id: UUID (FK -> Booking.id)

        scheduled_time: Timestamp

        status: Enum (Pending, Sent, Failed)

        retry_count: Integer

    AuditLog (Журнал аудиту)

        id: UUID (PK)

        user_id: UUID (FK -> User.id)

        action: String

        entity_type: Enum (Room, Booking, TimeSlot)

        entity_id: UUID

        timestamp: Timestamp

3. Зв'язки та кардинальність:

    User (Provider) ||--o{ Room: Один постачальник може керувати багатьма приміщеннями, кожне приміщення належить одному постачальнику.

    Room ||--o{ TimeSlot: Одне приміщення має багато часових слотів, слот належить одному приміщенню.

    User (Client) ||--o{ Booking: Один клієнт може мати багато бронювань, бронювання належить одному клієнту.

    TimeSlot ||--o{ Booking: Один часовий слот може мати історію бронювань (наприклад, скасовані та одне активне), бронювання стосується одного слота.

    Booking ||--o| Notification: Одне бронювання може мати одне заплановане сповіщення.

    User ||--o{ AuditLog: Один користувач може згенерувати багато записів аудиту.

Використання ШІ: у структуруванні документа та при додатковій перевірці відповідності стандартам завдання було використано ШІ Gemini (відповідно до ідей команди). Документ було перевірено, доповнено, відредаговано та затверджено учасниками команди.