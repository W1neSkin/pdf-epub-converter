-- PDF to EPUB Converter Database Schema
-- This schema works with Supabase built-in auth system

-- Enable Row Level Security
ALTER DATABASE postgres SET "app.jwt_secret" TO 'your-jwt-secret-here';

-- Create custom user profiles table (extends Supabase auth.users)
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    subscription_tier TEXT DEFAULT 'free',
    storage_used BIGINT DEFAULT 0, -- in bytes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create books table for user library
CREATE TABLE public.user_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size BIGINT NOT NULL, -- in bytes
    pages INTEGER,
    words INTEGER,
    cloudinary_url TEXT, -- For EPUB file storage
    cover_image_url TEXT, -- Book cover from Cloudinary
    file_path TEXT, -- Local file path for downloads
    metadata JSONB DEFAULT '{}', -- Additional book metadata
    is_public BOOLEAN DEFAULT FALSE, -- For sharing features
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create conversion history table
CREATE TABLE public.conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    book_id UUID REFERENCES public.user_books(id) ON DELETE SET NULL,
    original_filename TEXT NOT NULL,
    conversion_status TEXT DEFAULT 'processing', -- processing, completed, failed
    pages INTEGER,
    words INTEGER,
    processing_time INTEGER, -- in seconds
    error_message TEXT,
    conversion_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create shared books table (for sharing between users)
CREATE TABLE public.shared_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES public.user_books(id) ON DELETE CASCADE,
    owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    shared_with_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    permission_level TEXT DEFAULT 'read', -- read, download
    shared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(book_id, shared_with_id)
);

-- Create user sessions table (alternative to Redis)
CREATE TABLE public.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Row Level Security Policies

-- User profiles: Users can only see/edit their own profile
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON public.user_profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- User books: Users can only access their own books + shared books
ALTER TABLE public.user_books ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own books" ON public.user_books
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view public books" ON public.user_books
    FOR SELECT USING (is_public = TRUE);
CREATE POLICY "Users can view shared books" ON public.user_books
    FOR SELECT USING (
        id IN (
            SELECT book_id FROM public.shared_books 
            WHERE shared_with_id = auth.uid()
        )
    );
CREATE POLICY "Users can manage own books" ON public.user_books
    FOR ALL USING (auth.uid() = user_id);

-- Conversions: Users can only see their own conversions
ALTER TABLE public.conversions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own conversions" ON public.conversions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own conversions" ON public.conversions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own conversions" ON public.conversions
    FOR UPDATE USING (auth.uid() = user_id);

-- Shared books: Users can see books they've shared and books shared with them
ALTER TABLE public.shared_books ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their sharing activity" ON public.shared_books
    FOR SELECT USING (auth.uid() = owner_id OR auth.uid() = shared_with_id);
CREATE POLICY "Users can share their books" ON public.shared_books
    FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "Users can manage their shares" ON public.shared_books
    FOR ALL USING (auth.uid() = owner_id);

-- User sessions: Users can only access their own sessions
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own sessions" ON public.user_sessions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own sessions" ON public.user_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX idx_user_books_user_id ON public.user_books(user_id);
CREATE INDEX idx_user_books_created_at ON public.user_books(created_at DESC);
CREATE INDEX idx_conversions_user_id ON public.conversions(user_id);
CREATE INDEX idx_conversions_created_at ON public.conversions(created_at DESC);
CREATE INDEX idx_shared_books_shared_with ON public.shared_books(shared_with_id);
CREATE INDEX idx_user_sessions_token ON public.user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON public.user_sessions(expires_at);

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON public.user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_books_updated_at 
    BEFORE UPDATE ON public.user_books 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM public.user_sessions 
    WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql; 