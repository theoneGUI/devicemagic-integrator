# devicemagic-integrator
Creates a database bridge between ServiceTrade and DeviceMagic's ability to integrate with an SQL database.

ServiceTrade is a service software and it offers a webhook and API to allow other apps to integrate.

Device Magic is a software that allows you to create forms for technicians or other employees to fill out in a standard format you set.

This software creates a bridge that allows Device Magic's Resources to essentially connect to ServiceTrade's database, even though there is no real way to do this through either software internally.

Device Magic Integrator will keep an up-to-date database of what assets and services are stored in ServiceTrade. It updates based on whenever a location, job, or appointment are updated. It then reaches out to ServiceTrade in order to view the change, addition, or deletion of an object of interest and records whatever change happened in the database.

Device Magic can then use the database as a Resource and then be used in creating forms that have content generated based on current ServiceTrade information.

## Experimental vs Not
There is an experimental folder which contains code that is more efficient in how it handles the webhook's communications, but it crashes more often and I haven't put that much time in to fix it. It uses threading and a Set object to process only as much as it needs to at a given time.

The main directory of the repository has a much less elegant solution to the problem and processes everything thrown at it. Running on a 1 core VPS, it will often lock up for minutes at a time. Thus, experimental was created.

My personal workaround to the problem of Experimental crashing is a scheduled `systemctl restart` every hour. It's not great but it works.
