-- Add RLS policy exceptions for service role operations
-- This allows the auth service to create user profiles during registration

-- Add service role bypass for user_profiles INSERT
CREATE POLICY "Service role can insert profiles" ON public.user_profiles
    FOR INSERT WITH CHECK (
        auth.uid() = id OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- Add service role bypass for health checks
CREATE POLICY "Service role can read for health checks" ON public.user_profiles
    FOR SELECT USING (
        auth.uid() = id OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- Apply same logic to other tables for service operations
CREATE POLICY "Service role can read user_books" ON public.user_books
    FOR SELECT USING (
        auth.uid() = user_id OR
        is_public = TRUE OR
        id IN (SELECT book_id FROM public.shared_books WHERE shared_with_id = auth.uid()) OR
        auth.jwt() ->> 'role' = 'service_role'
    );

CREATE POLICY "Service role can read conversions" ON public.conversions
    FOR SELECT USING (
        auth.uid() = user_id OR
        auth.jwt() ->> 'role' = 'service_role'
    ); 