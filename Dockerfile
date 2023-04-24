
FROM python:3.8-alpine

# activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY . .
RUN pip install -r requirements.txt
# copy every content from the local file to the image
RUN pip install waitress
#CMD waitress-serve --host 0.0.0.0 --call website:create_app --url_scheme https
# configure the container to run in an executed manner
ENTRYPOINT ["python"]
CMD ["app.py"]
