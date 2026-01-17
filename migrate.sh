#!/bin/bash
flask db upgrade && gunicorn "app:create_app()"
