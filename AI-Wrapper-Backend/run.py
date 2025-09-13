from application import create_app

# The factory creates a fully configured app for us
app, api, celery = create_app()

if __name__ == "__main__":
    app.run(debug=True)