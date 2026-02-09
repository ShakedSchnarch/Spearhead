from spearhead.api.deps import get_db

if __name__ == "__main__":
    print("Initializing Database...")
    db = get_db()
    print(f"Database initialized at: {db.db_path.resolve()}")
    
    # Run Sync
    from spearhead.data.import_service import ImportService
    from spearhead.sync.google_sheets import GoogleSheetsProvider, SyncService
    from spearhead.config import settings

    print("Starting Data Sync...")
    import_service = ImportService(db_path=db.db_path)
    provider = GoogleSheetsProvider(
        service_account_file=settings.google.service_account_file,
        api_key=settings.google.api_key
    )
    # Mocking cache dir or using real logic? Using real logic
    svc = SyncService(
        import_service=import_service,
        provider=provider,
        file_ids=settings.google.file_ids,
        cache_dir=settings.google.cache_dir
    )
    
    try:
        report = svc.sync_all()
        print("Sync Report:", report)
    except Exception as e:
        print(f"Sync Failed: {e}")

    print("Done.")
