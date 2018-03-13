
sample HDf File: I tried to construct a sample HDF File based on ICM data structure given here https://icmplus.neurosurg.cam.ac.uk/home/icm-features/hdf5-new-icm-data-format

IPython Notebook and Data file Generated are present in Data Folder in current Directory( Same Data file is also put in /data/public folder for H5serv use)

Testing in R: To test the h5serv library with R, I created a R notebook which is present in R folder in this Directory, Its generated Html file can be used to see the Result.

Testing in Python: Similar to R I also tried testinng H5serv library in Python. A python Notebook is present in Python folder in this directory showing the Result.


Configuration File has been changed to use domain name -- icmplus.neurosurg.cam.ac.uk

Result: As per my observation H5serv library can fulfill our purpose by granularizing Data as it support options like:

Select- select a part of Dataset
where- use to select data that satisfies a condition
query- use multiple conditons for finer control on data  

