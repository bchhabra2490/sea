-- Supabase Storage bucket for uploaded CSV / JSONL proof files
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'proofs',
    'proofs',
    false,
    52428800,
    array[
        'text/plain',
        'text/csv',
        'application/json',
        'application/jsonl',
        'application/csv',
        'application/octet-stream'
    ]
)
on conflict (id) do update set
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- Service role (backend) can manage all objects in proofs
create policy "Service role full access to proofs"
on storage.objects
for all
to service_role
using (bucket_id = 'proofs')
with check (bucket_id = 'proofs');

-- Authenticated users can read their uploads (adjust when auth is added)
create policy "Authenticated read proofs"
on storage.objects
for select
to authenticated
using (bucket_id = 'proofs');

-- Authenticated users can upload to proofs/{user_id}/...
create policy "Authenticated upload proofs"
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'proofs'
    and (storage.foldername(name))[1] = auth.uid()::text
);

comment on table storage.buckets is 'proofs bucket stores raw CSV and JSONL conversation uploads';
