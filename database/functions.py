from database.database import Database

async def init_db():
    async with Database() as db:
        try:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS public.images
(
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 99999999999999 CACHE 1 ),
    image bytea NOT NULL,
    CONSTRAINT images_pkey PRIMARY KEY (id)
)""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS public.videos
(
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 99999999999999 CACHE 1 ),
    video bytea NOT NULL,
    CONSTRAINT videos_pkey PRIMARY KEY (id)
)""")
        except Exception as e:
            print(f"Ошибка при создании таблицы: {e}")