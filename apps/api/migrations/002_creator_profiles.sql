CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO categories (id, slug, name) VALUES
    ('00000000-0000-4000-8000-000000000001', 'programacao', 'Programação'),
    ('00000000-0000-4000-8000-000000000002', 'ia', 'IA'),
    ('00000000-0000-4000-8000-000000000003', 'design', 'Design'),
    ('00000000-0000-4000-8000-000000000004', 'edicao-de-video', 'Edição de vídeo'),
    ('00000000-0000-4000-8000-000000000005', 'marketing', 'Marketing'),
    ('00000000-0000-4000-8000-000000000006', 'dados', 'Dados'),
    ('00000000-0000-4000-8000-000000000007', 'producao-musical', 'Produção musical'),
    ('00000000-0000-4000-8000-000000000008', 'cad', 'CAD'),
    ('00000000-0000-4000-8000-000000000009', 'arquitetura', 'Arquitetura'),
    ('00000000-0000-4000-8000-000000000010', 'seguranca', 'Segurança'),
    ('00000000-0000-4000-8000-000000000011', 'planilhas', 'Planilhas'),
    ('00000000-0000-4000-8000-000000000012', 'automacao', 'Automação'),
    ('00000000-0000-4000-8000-000000000013', 'games', 'Games'),
    ('00000000-0000-4000-8000-000000000014', 'suporte-tecnico', 'Suporte técnico'),
    ('00000000-0000-4000-8000-000000000015', 'educacao', 'Educação'),
    ('00000000-0000-4000-8000-000000000016', 'mentoria', 'Mentoria')
ON CONFLICT (id) DO UPDATE SET slug=EXCLUDED.slug, name=EXCLUDED.name;

CREATE TABLE IF NOT EXISTS creator_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    photo_url TEXT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    bio TEXT NOT NULL DEFAULT '',
    profession TEXT NOT NULL CHECK (length(trim(profession)) > 0),
    specialties TEXT[] NOT NULL DEFAULT '{}',
    tools TEXT[] NOT NULL DEFAULT '{}',
    languages TEXT[] NOT NULL DEFAULT '{}',
    social_links JSONB NOT NULL DEFAULT '{}',
    is_verified BOOLEAN NOT NULL DEFAULT false,
    default_price NUMERIC(10,2) CHECK (default_price >= 0),
    accepts_tips BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS creator_categories (
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    PRIMARY KEY (creator_id, category_id)
);
CREATE INDEX IF NOT EXISTS creator_categories_category_id_idx
    ON creator_categories(category_id);
