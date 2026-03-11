pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
if [ "$RENDER_SEED_DEMO_DATA" = "1" ]; then
  python manage.py seed_demo_data
fi
