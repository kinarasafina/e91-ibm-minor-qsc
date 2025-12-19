# e91-ibm-minor-qsc

1. python -m venv .venv
2. .venv\Scripts\activate
3. pip install -r requirements.txt

## Running the assigments on IBM Cloud

1. Create a `.env` file in the root directory
2. Fill in the API key and the instance name using this template:

   ```python
   API_KEY=<api_key>
   INSTANCE_NAME=<instance_name>
   ```

3. Change the `USE_IBM_CLOUD` variable to True in the assignment of choice
4. Run the assignments
