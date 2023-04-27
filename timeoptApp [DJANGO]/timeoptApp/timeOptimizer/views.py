from django.shortcuts import render
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import optDataSerializer, optResultsSerializer, allCourses
from .models import HEI, course, Lecturer, semester, courseContent, courseDidactic, coursePresentation, courseImpact, courseLectTime, courseStudentCount, optData, optResults
from .forms import courseForm, optDataForm, lecturerRegistrationForm, LoginForm, LecturerUpdateForm

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages

from django.contrib.auth.decorators import login_required

import datetime
from django.db.models import Q

import json
import copy

import os
from django.conf import settings
from PIL import Image

#page with all optimization data(course configurations entered by lecturers)
def home(request):
    optiData = optData.objects.all()
    serializer = optDataSerializer(optiData, many=True)
    return JsonResponse({'optimizationDataConfigs': serializer.data}, safe=False)

# @login_required
def login_view(request):
    #here I check if there's a semester object with current(or next) semester's name and create if necessary
    current_year = datetime.datetime.now().year
    ws_sem = "WS" + str(current_year) + "/" + str(current_year + 1)   #next WS if currently in SS current year
    ss_sem = "SS" + str(current_year + 1)   #next SS if currently in WS 

    if len(semester.objects.filter(Q(semester_name = ws_sem) | Q(semester_name = ss_sem))) == 2:
        pass
    else: 
        ws_sem_obj = semester.objects.create(semester_name = ws_sem, semesterModules = {}, coursesInSemester = {})
        ss_sem_obj = semester.objects.create(semester_name = ss_sem, semesterModules = {}, coursesInSemester = {})

    logout(request) # first log out current user 

    if request.method == "POST":
        form = LoginForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username = username, password = password, backend='timeOptimizer.backends.CustomAuthBackend')
            if user is not None:
                login(request, user)
                messages.success(request, "You've been logged in")
                return redirect('profile_view')
            else: 
                messages.error(request, "Invalid username or password")
                return render(request, "registration/login.html", {"form": form})
        else:
            messages.error(request, "Please enter a valid username and password.")
            return render(request, "registration/login.html", {"form": form})
    else:
        form = LoginForm()
        return render(request, "registration/login.html", {"form": form})
    

def profile_view(request):
        
        currentUser = request.user

        currentLecturer = Lecturer.objects.filter(user = currentUser)[0]
        # semTimeform = semesterTimeForm(instance=currentLecturer)
        LecturerForm = LecturerUpdateForm(instance=currentLecturer)
        course_form = courseForm()
        all_courses = course.objects.all()

        currentLecturer = request.user.lecturer_profile
        list_of_courses = currentLecturer.courseOffered 

        other_courses = all_courses.exclude(id__in = list_of_courses.values_list('id', flat = True))
        content = {'course_form': course_form,
                #    'semTimeform' : semTimeform,
                    'all_semesters': semester.objects.all(),
                    'LecturerForm': LecturerForm,
                    'other_courses': other_courses}

        if request.method == 'POST':
            if 'course_form-submit' in request.POST:
                newCourse = courseForm(request.POST)
                if newCourse.is_valid():
                    print(newCourse.cleaned_data['course_name'])
                    list_of_duplicate_courses_all = [ cour for cour in course.objects.all() if cour.course_name == newCourse.cleaned_data['course_name']]

                    currentLecturer = request.user.lecturer_profile
                    list_of_duplicate_courses_user = [ cour for cour in currentLecturer.courseOffered.all() if cour.course_name == newCourse.cleaned_data['course_name']]

                    #if in both course lists
                    if len(list_of_duplicate_courses_all) > 0 and len(list_of_duplicate_courses_user) > 0:  
                            messages.error(request, str(newCourse.cleaned_data['course_name']) + " *already exists! Please check list on the left*")
                            print("not created!!!")
                            return render(request, 'profile.html', content)
                    
                    #if in courses but not in lect_courseOffered
                    elif len(list_of_duplicate_courses_all) > 0 and len(list_of_duplicate_courses_user) == 0:  
                        messages.error(request, str(newCourse.cleaned_data['course_name']) + " *already exists! Please check list on the left*")
                        return render(request, 'profile.html', content)
                        
                    # test for list of all courses    
                    elif len(list_of_duplicate_courses_all) > 0: 
                        messages.error(request, "course already exists (TEST) !")
                        return render(request, 'profile.html', content)
                    
                    # if in none of course lists
                    else: 
                        new_course = newCourse.save()
                        #now assign name of lecturer creating the course, then save again
                        new_course.lecturer_name = currentLecturer.lecturer_name 
                        new_course.save()
                        currentLecturer = request.user.lecturer_profile
                        currentLecturer.courseOffered.add(new_course)
                        # return redirect('profile_view')
                        return render(request, 'profile.html', content)
                                

            if 'updateLecturer-submit' in request.POST:
                updateLecturerForm = LecturerUpdateForm(request.POST, instance=currentLecturer)
                if updateLecturerForm.is_valid():
                    currentLecturer.lecturer_name = updateLecturerForm.cleaned_data['lecturer_name']
                    currentUser.username = updateLecturerForm.cleaned_data['lecturer_name']
                    currentLecturer.title = updateLecturerForm.cleaned_data['title']
                    currentLecturer.lecturer_email = updateLecturerForm.cleaned_data['lecturer_email']
                    currentUser.email = currentLecturer.lecturer_email
                    currentUser.save()
                    currentLecturer.picked_semester.set([updateLecturerForm.cleaned_data['picked_semester'].first().id])
                    currentLecturer.time_available = updateLecturerForm.cleaned_data['time_available']
                    currentLecturer.save()

                    updateLecturerForm.save()
                    return redirect('profile_view')

                else:
                    return redirect('profile_view')

        return render(request, 'profile.html', content)


def register_view(request):
    if request.method == "POST":
        form = lecturerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'timeOptimizer.backends.CustomAuthBackend'
            login(request, user)
            return redirect('profile_view')
    else:
        form = lecturerRegistrationForm()
    return render(request, 'registration/registration.html', {'form': form})
    

#this get's the opt_data's id and sends to spring boot api for optimization calculations (also creates the corresponding opt_results)
def optimizerWebService(request, optDataID):

    current_lecturer = request.user.lecturer_profile

    optData_ready = optData.objects.get(id = optDataID)

    #test if optData_ready already has an optMethod:
    if optData_ready.optMethod == "":
        messages.error(request, "please select an optimization method ") 
        return redirect ('allCourseParameters')
    else:

        #list of optDatas with same course parameters
        list_of_dups = list(optData.objects.filter(lecturer = current_lecturer, courses = optData_ready.courses))

        # create a set of already used optMethods ( use a set to avoid duplicates)
        set_of_already_used_optMethods = set([obj.optMethod for obj in list_of_dups])

        if checkDups(request, optData_ready.pk) == True:
            list_of_optData_dups = list_of_dups
            print( "This already has dups ", list_of_optData_dups)

        # control if set_of_already_used_optMethods is empty, meaning no optMethod was choosen yet and might create an unwanted duplicate of optData later ---- create the other optDatas and corresponding optResults where necessary
        # elif len(set_of_already_used_optMethods) is not 0:
        else:
            list_of_optMethods = [method[0] for method in optData.OptimizationMethods]

            list_of_optMethods_to_create = [method for method in list_of_optMethods if method not in set_of_already_used_optMethods]

            #check 
            for method in list_of_optMethods_to_create:
                if optData_ready.optMethod == method:
                    pass
                else: 
                    new_optData = optData.objects.create(   semesterName = optData_ready.semesterName,
                                                            totalHours = optData_ready.totalHours,
                                                            optMethod = method,
                                                            courses = optData_ready.courses,
                                                            lecturer = optData_ready.lecturer,
                                                            picked_course = None
                                                            
                                                        ) 
                    new_optData.save()
                    
                    new_optResult = optResults.objects.create(  semesterName = new_optData.semesterName, 
                                                                totalHours = new_optData.totalHours,
                                                                optMethod = new_optData.optMethod,
                                                                optimizationResults = {},
                                                                optDataObj = new_optData, 

                                                            )   
                    new_optResult.save()

        # Now we filter through all the optData of the lecturer, using courses as filter criteria to see if identical
        list_of_optData_dups = list(optData.objects.filter(lecturer = current_lecturer, courses = optData_ready.courses))
        print(list_of_optData_dups)

        all_optDatas_lecturer = optData.objects.filter(lecturer = current_lecturer)
        filtered_list_no_dups = [obj for obj in all_optDatas_lecturer if obj not in list_of_optData_dups]

        # For evaluation we compute the optimization for the same data but different optMethods in a loop: 

        for opt_obj in list_of_optData_dups:
            serializer = optDataSerializer(opt_obj)
            json_obj = serializer.data

            corresponding_optresults = optResults.objects.filter(optDataObj = opt_obj)[0] #get the opt_result object for chosen opt_data

            url = 'http://localhost:8080/api/optimize'
            headers = {'Content-type': 'application/json'}
            response = requests.post(url, json = json_obj, headers = headers)

            if response.status_code == 200:

                display_response = json.loads(response.content.decode())  #response from spring boot web service

                optimization_results_json = {}

                for (k,v) in display_response['courses'].items():
                    optimization_results_dic = {}
                    optimization_results_dic[str(v['Course name'])] =  { 'Scientific content percentage' : v['Scientific content percentage'], 
                                                                        'Hours for scientific content': v['Hours for scientific content'],
                                                                        'Didactic percentage': v['Didactic percentage'],
                                                                        'Hours for didactics': v['Hours for didactics'],
                                                                        'Presentation percentage': v['Presentation percentage'],
                                                                        'Hours for presentation': v['Hours for presentation']
                    }
                    optimization_results_json.update(optimization_results_dic)

                corresponding_optresults.optimizationResults = optimization_results_json #overwritting previous json object with new opt_results

                #display msg "(new)" if just computed
                current_optData_list = optData.objects.filter(lecturer = current_lecturer)

                # #after optimization computation, the main optData is added back to list that'll be displayed:
                # filtered_list_no_dups.append(optData_ready)

                #update status to signal results ready
                for opt_data in filtered_list_no_dups:
                        if opt_data.opt_results == corresponding_optresults:
                            corresponding_optresults.update_status = "(new)"
                        else:
                            opt_data.opt_results.update_status = ""
                            opt_data.opt_results.save()
                corresponding_optresults.save()          

            else:
                # Handle the error
                pass

                return HttpResponse("Something went wrong!")

        return redirect('allCourseParameters')






def createOptData(request):

    #verify if optData has already been created
    
    currentLecturer = request.user.lecturer_profile

    if currentLecturer.picked_semester.first() is None:
        messages.error(request, "Please select a semester before proceeding!")
        return redirect('profile_view')
    elif currentLecturer.time_available == 0:
        messages.error(request, "Please enter time available for the semester preparation before proceeding!")
        return redirect('profile_view')
    else: 
        #creating a new optData set
        obj = optData.objects.create(semesterName = currentLecturer.picked_semester.first().semester_name,
                                            totalHours = currentLecturer.time_available,
                                            optMethod = "",
                                            courses = {},
                                            lecturer = currentLecturer,)
        print(obj.pk)

        form = optDataForm(initial={'semesterName': currentLecturer.picked_semester, 'totalHours': currentLecturer.time_available, 'lecturer': currentLecturer})

        data = {}
        course_config = {'courseContent': {'CourseComplexity': 0.0, 'CourseFamiliarity': 0.0, 'contentWeight': 1.0, 'norm_contentWeight': 1.0},
                            'courseDidactic': {'CourseComplexity': 0.0, 'CourseFamiliarity': 0.0, 'didacticWeight': 1.0, 'norm_didacticWeight': 1.0},
                            'coursePresentation': {'finished': 0.0, 'time0': 0.0, 'pres0': 0.0, 'complexity': 0.0, 'presentationWeight': 1.0, 'norm_presentationWeight': 1.0},
                            'courseImpact': {'d': 0.0},
                            'courseLectTime': {'d': 0.0},
                            'courseStudentCount': {'students': 0},
                            }

        for course in request.user.lecturer_profile.courseOffered.all():
            data[course.course_name] = course_config
            print(course.course_name, data[course.course_name])

        obj.courses = data
        obj.save()
        print(obj.pk)

        # create it's corresponding opt_results 
        obj_opt_results = optResults.objects.create(semesterName = obj.semesterName,
                                totalHours = obj.totalHours,
                                optMethod = obj.optMethod,
                                optimalValue = 0.0, 
                                optimizationResults = {}, 
                                optDataObj = obj)
        
        obj_opt_results.save()     
        print("this is the new pk: " + str(obj_opt_results.pk))  

        current_optData = optData.objects.filter(lecturer = currentLecturer).last()
        context = {'current_optData': current_optData,
                'form': form,
                #    'form': optDataForm(),
        }
        return render(request, 'optData.html', context)




def config_page(request):
    currentLecturer = request.user.lecturer_profile
    current_optData = optData.objects.filter(lecturer = currentLecturer).last()
    context = {'current_optData': current_optData,
               
               'form': optDataForm(),
    }
    return render(request, 'optData.html', context)


    
@login_required
def deleteCourse(request, course_id):
    #selected_course = course.objects.filter(id = course_id)
    currentLecturer = request.user.lecturer_profile

    for cour in currentLecturer.courseOffered.all():
        if cour.id == course_id:
            selected_course = cour
            currentLecturer.courseOffered.remove(selected_course)
            print(len(currentLecturer.courseOffered.all()))
            print("Hello WOrld")
    return redirect('profile_view')



def addCourseParameter(request, id):
    instance_obj = optData.objects.get(id = id)

    instanceForm = optDataForm(instance=optData.objects.get(pk = id))

    if request.method == 'POST':
        instance_obj.totalHours = request.POST['totalHours']
        instance_obj.semesterName = request.POST['semesterName']
        instance_obj.optMethod = request.POST['optMethod']

        # notice request.POST['picked_course'] returns "id" of a course-> we're going to get the id from all objects of courses
        selected_course = course.objects.get(id=int(request.POST['picked_course']))

        instance_obj.picked_course = selected_course

        json_data = instance_obj.courses
        key = instance_obj.picked_course.course_name  #name of courses in json object as keys

        if key not in json_data :
            data = {}

            course_config = {'courseContent': {'CourseComplexity': 0, 'CourseFamiliarity': 0},
                            'courseDidactic': {'CourseComplexity': 0, 'CourseFamiliarity': 0},
                            'coursePresentation': {'finished': 0, 'time0': 0, 'pres0': 0, 'complexity': 0},
                            'courseImpact': {'d': 0},
                            'courseLectTime': {'d': 0},
                            'courseStudentCount': {'students': 0},
                            }

            course_config['courseContent']['CourseComplexity'] = request.POST['courseContentComplexity']
            course_config['courseContent']['CourseFamiliarity'] = request.POST['courseContentFamiliarity']

            course_config['courseDidactic']['CourseComplexity'] = request.POST['courseDidacticComplexity']
            course_config['courseDidactic']['CourseFamiliarity'] = request.POST['courseDidacticFamiliarity']

            course_config['coursePresentation']['finished'] = request.POST['coursePresentationFinished']
            course_config['coursePresentation']['time0'] = request.POST['coursePresentationTime0']
            course_config['coursePresentation']['pres0'] = request.POST['coursePresentationPres0']
            course_config['coursePresentation']['complexity'] = request.POST['coursePresentationComplexity']

            course_config['courseImpact']['d'] = request.POST['courseImpact']

            course_config['courseLectTime']['d'] = request.POST['courseLectTime']

            course_config['courseStudentCount']['students'] = request.POST['courseStudentCount']

            data[key] = course_config

            json_data.update(data)

            #adjusting JSONField's structure to look more spaced and readable   
            #Notice this works, it gives it the original structure(ordered respected) you defined, but it's not displayed on screen with identations/spacing
            # organized_json_data = json.dumps(json_data, indent=4, sort_keys=True)

            instance_obj.courses = json_data
            instance_obj.save()            

            # form = optDataForm()
            context = {'form': instanceForm,
                    'all_params': optData.objects.all(),
                    }
            return render(request, 'optData.html', context )
            # return render(request, 'optimizationPage.html', context)
        else:
            json_data[key]['courseContent']['CourseComplexity'] = request.POST['courseContentComplexity']
            json_data[key]['courseContent']['CourseFamiliarity'] = request.POST['courseContentFamiliarity']

            json_data[key]['courseDidactic']['CourseComplexity'] = request.POST['courseDidacticComplexity']
            json_data[key]['courseDidactic']['CourseFamiliarity'] = request.POST['courseDidacticFamiliarity']

            json_data[key]['coursePresentation']['finished'] = request.POST['coursePresentationFinished']
            json_data[key]['coursePresentation']['time0'] = request.POST['coursePresentationTime0']
            json_data[key]['coursePresentation']['pres0'] = request.POST['coursePresentationPres0']
            json_data[key]['coursePresentation']['complexity'] = request.POST['coursePresentationComplexity']

            json_data[key]['courseImpact']['d'] = request.POST['courseImpact']

            json_data[key]['courseLectTime']['d'] = request.POST['courseLectTime']

            json_data[key]['courseStudentCount']['students'] = request.POST['courseStudentCount']

            instance_obj.courses = json_data
            instance_obj.save() 

            context = {'form': instanceForm}
            return render(request, 'optData.html', context )

    context = {'form': instanceForm}
    return render(request, 'optData.html', context ) 


def allCourseParameters(request):
    display_filtered_optData = []
    optiResults = []

    currentLecturer = request.user.lecturer_profile

    #eliminate duplicates created during optimization:
    optData_list = optData.objects.filter(lecturer = currentLecturer).order_by('-edited_at')
    optData_list_no_dups = []

    for opt_obj in optData_list: 
        dups = optData.objects.filter(lecturer=currentLecturer, courses=opt_obj.courses).exclude(pk=opt_obj.pk).order_by('-edited_at')

        if not dups.exists():

            optData_list_no_dups.append(opt_obj)
            display_filtered_optData += optData_list_no_dups
            optiResults += optResults.objects.filter(optDataObj__in = display_filtered_optData)

        else: 
            # get oldest optData to know which was created first, hence making the others be the latest/copies
            oldest_optData = optData.objects.filter(lecturer=currentLecturer, courses=opt_obj.courses).order_by('-created_at')[0]

            dups = optData.objects.filter(lecturer=currentLecturer, courses=opt_obj.courses).exclude(pk = oldest_optData.pk)

            display_filtered_optData += [obj for obj in optData_list if obj not in dups]
            optiResults += optResults.objects.filter(optDataObj__in = display_filtered_optData)

    context = {'all_params': set(display_filtered_optData), 
                'all_results_serializer': set(optiResults),
                # 'dups': dups,
                }
    return render(request, 'optimizationPage.html', context)

# else:
#     messages.error(request, 'no optimization data yet ') 
#     return render(request, 'optimizationPage.html', {})    

    # if optiData: 
    #     optiData = optData.objects.filter(lecturer = currentLecturer).order_by('-edited_at')
    #     optiResults = optResults.objects.filter(optDataObj__in = optiData)  #.order_by('-created_at')
    #     context = {'all_params': optiData, 
    #                'all_results_serializer': optiResults}
    #     return render(request, 'optimizationPage.html', context)
    # else:
    #     messages.error(request, 'no optimization data yet ') 
    #     return render(request, 'optimizationPage.html', {})    



def updateForm(request):
    if request.is_ajax() and request.method == 'POST':
        current_form_idx = request.POST.get('current_form_index')
        current_form_data = request.POST.get('current_form_data')

        opt_data = optData.objects.get(id = current_form_idx)
        for k,v in current_form_data.items():
            opt_data.courses[k] = v
            opt_data.save()

            return JsonResponse({'success': True})
        return JsonResponse({'success': False})


def editCourse(request, optData_id, key):
    
    print(key)

    currentLecturer = request.user.lecturer_profile

    current_optData = optData.objects.get(id = optData_id)
    current_optData.picked_course = course.objects.get(course_name = key)
    current_course = current_optData.courses[key]
    current_form = optDataForm(instance=current_optData)

    old_current_optData = copy.deepcopy(current_optData.courses) 

    #We find the dups and update them too: 
    dups_list = list(optData.objects.filter(lecturer = currentLecturer, courses = current_optData.courses).exclude(id = optData_id))
    print("list of dups w/o the current Optdata ", dups_list)


    if request.method == 'POST':
        
        form = optDataForm(request.POST)
        if form.is_valid() and current_optData.picked_course is not None:
            current_course['courseContent']['CourseComplexity'] = str(form.cleaned_data['courseContentComplexity'])
            current_course['courseContent']['CourseFamiliarity'] = str(form.cleaned_data['courseContentFamiliarity'])
            current_course['courseContent']['contentWeight'] = str(form.cleaned_data['courseContentWeight'])
            current_course['courseDidactic']['CourseComplexity'] = str(form.cleaned_data['courseDidacticComplexity'])
            current_course['courseDidactic']['CourseFamiliarity'] = str(form.cleaned_data['courseDidacticFamiliarity'])
            current_course['courseDidactic']['didacticWeight'] = str(form.cleaned_data['courseDidacticWeight'])
            current_course['coursePresentation']['finished'] = str(form.cleaned_data['coursePresentationFinished'])
            current_course['coursePresentation']['time0'] = str(form.cleaned_data['coursePresentationTime0'])
            current_course['coursePresentation']['pres0'] = str(form.cleaned_data['coursePresentationPres0'])
            current_course['coursePresentation']['complexity'] = str(form.cleaned_data['coursePresentationComplexity'])
            current_course['coursePresentation']['presentationWeight'] = str(form.cleaned_data['coursePresentationWeight'])
            current_course['courseImpact']['d'] = str(form.cleaned_data['courseImpact'])
            current_course['courseLectTime']['d'] = str(form.cleaned_data['courseLectTime'])
            current_course['courseStudentCount']['students'] = str(form.cleaned_data['courseStudentCount'])

            current_optData.optMethod = str(form.cleaned_data['optMethod'])
            print("debug test" + str(current_optData.optMethod))

            if json.dumps(old_current_optData) == json.dumps(current_optData.courses):

                print("The two JSON objects are the same")

            else:
                current_optData.opt_results.status = "update results for applied changes"
                current_optData.opt_results.save()

                print("The two JSON objects are different")
    
            current_optData.picked_course = None

            # we normalize the weights of the different course aspects
            sumOfWeights = form.cleaned_data['courseContentWeight'] + form.cleaned_data['courseDidacticWeight'] + form.cleaned_data['coursePresentationWeight']

            current_course['courseContent']['norm_contentWeight'] = str(form.cleaned_data['courseContentWeight'] / sumOfWeights)

            current_course['courseDidactic']['norm_didacticWeight'] = str(form.cleaned_data['courseDidacticWeight'] / sumOfWeights)

            current_course['coursePresentation']['norm_presentationWeight'] = str(form.cleaned_data['coursePresentationWeight'] / sumOfWeights)

            current_optData.courses[key] = current_course  #assign new values to the course dict of the optData

            current_optData.save()


            #update courses for all in dups_list then save:
            for obj in dups_list:
                obj.courses = current_optData.courses
                obj.save()

            messages.success(request, "successfully updated! ")

            context = {'all_params': optData.objects.filter(lecturer = currentLecturer),
                       'current_optData': current_optData,
                       }
            return render(request, 'optData.html', context)
        else: 

            messages.error(request, "please select a course on the left then fill the form correctly")

            current_form.fields['courseContentComplexity'].initial = current_course['courseContent']['CourseComplexity']
            current_form.fields['courseContentFamiliarity'].initial = current_course['courseContent']['CourseFamiliarity']
            current_form.fields['courseContentWeight'].initial = current_course['courseContent']['contentWeight']
            current_form.fields['courseDidacticComplexity'].initial = current_course['courseDidactic']['CourseComplexity']
            current_form.fields['courseDidacticFamiliarity'].initial = current_course['courseDidactic']['CourseFamiliarity']
            current_form.fields['courseDidacticWeight'].initial = current_course['courseDidactic']['didacticWeight']
            current_form.fields['coursePresentationFinished'].initial = current_course['coursePresentation']['finished']
            current_form.fields['coursePresentationTime0'].initial = current_course['coursePresentation']['time0']
            current_form.fields['coursePresentationPres0'].initial = current_course['coursePresentation']['pres0']
            current_form.fields['coursePresentationComplexity'].initial = current_course['coursePresentation']['complexity']
            current_form.fields['coursePresentationWeight'].initial = current_course['coursePresentation']['presentationWeight']
            current_form.fields['courseImpact'].initial = current_course['courseImpact']['d']
            current_form.fields['courseLectTime'].initial = current_course['courseLectTime']['d']
            current_form.fields['courseStudentCount'].initial = current_course['courseStudentCount']['students']

            #In case form didn't submit properly:
            current_optData.picked_course = None

            context = {'form': current_form, 
                        'current_optData': current_optData,
                        'form_errors': form.errors,
            }

            print(form.errors.as_data())
            return render(request, 'optData.html', context)

            
    
    else: 
        # current_form.fields['picked_course'].initial = course.objects.get(course_name = key)
        current_form.fields['courseContentComplexity'].initial = current_course['courseContent']['CourseComplexity']
        current_form.fields['courseContentFamiliarity'].initial = current_course['courseContent']['CourseFamiliarity']
        current_form.fields['courseContentWeight'].initial = current_course['courseContent']['contentWeight']
        current_form.fields['courseDidacticComplexity'].initial = current_course['courseDidactic']['CourseComplexity']
        current_form.fields['courseDidacticFamiliarity'].initial = current_course['courseDidactic']['CourseFamiliarity']
        current_form.fields['courseDidacticWeight'].initial = current_course['courseDidactic']['didacticWeight']
        current_form.fields['coursePresentationFinished'].initial = current_course['coursePresentation']['finished']
        current_form.fields['coursePresentationTime0'].initial = current_course['coursePresentation']['time0']
        current_form.fields['coursePresentationPres0'].initial = current_course['coursePresentation']['pres0']
        current_form.fields['coursePresentationComplexity'].initial = current_course['coursePresentation']['complexity']
        current_form.fields['coursePresentationWeight'].initial = current_course['coursePresentation']['presentationWeight']
        current_form.fields['courseImpact'].initial = current_course['courseImpact']['d']
        current_form.fields['courseLectTime'].initial = current_course['courseLectTime']['d']
        current_form.fields['courseStudentCount'].initial = current_course['courseStudentCount']['students']


    context = {'form': current_form, 
               'current_optData': current_optData,
               }
    return render(request, 'optData.html', context ) 
        

def delete_optCourse(request, optData_id, key):

    print(key)
    print(optData_id)
    # currentLecturer = request.user.lecturer_profile

    current_optData = optData.objects.get(id = optData_id)

    current_form = optDataForm(instance=current_optData)

    del current_optData.courses[key]
    current_optData.save()

    print(current_optData.courses)

    context = {'form': current_form, 
               'current_optData': current_optData,
               }
    return render(request, 'optData.html', context ) 

    

def delete_optData(request, optData_id):

    currentLecturer = request.user.lecturer_profile
    selected_optData = optData.objects.get(id = optData_id)

    dups_list = optData.objects.filter(lecturer = currentLecturer, courses = selected_optData.courses)

    for obj in dups_list:

        print(optData_id)
        obj.delete()

    return redirect('allCourseParameters')


def logout_view(request):
    logout(request)
    return redirect('login_view')



def addCourse(request, cour_id):
    selected_course = course.objects.get(id = cour_id)
    currentLecturer = request.user.lecturer_profile
    list_of_courses = currentLecturer.courseOffered 

    list_of_courses.add(selected_course)
    currentLecturer.save()

    return redirect('profile_view')


def optimizationOverview(request, optData_id):
    currentLecturer = request.user.lecturer_profile

    try:
        current_optData = optData.objects.filter(id = optData_id)[0]
        optData_list_curr_user = optData.objects.filter(lecturer = currentLecturer)
        dups = [obj for obj in optData_list_curr_user if obj.courses == current_optData.courses ]

        context = { "all_dups": dups,
        }

        return render(request, 'optimizationWrap.html', context)
    
    except IndexError:

        dups = []
        context = { "all_dups": dups,
        }
        print("The index is out of range.")
        return render(request, 'optimizationWrap.html', context)
    

def editCourseDetail(request, course_id): 
    selectedCourse = course.objects.get(id = course_id) 
    course_form = courseForm(instance=selectedCourse)
    selectedCourseForm = courseForm()

    if request.method == "POST":
        course_form = courseForm(request.POST, instance=selectedCourse)
        if course_form.is_valid():
            course_form.save()
            return redirect('profile_view')

    else: 
        currentUser = request.user
        currentLecturer = Lecturer.objects.filter(user = currentUser)[0]
        # semTimeform = semesterTimeForm(instance=currentLecturer)
        LecturerForm = LecturerUpdateForm(instance=currentLecturer)
        all_courses = course.objects.all()

        currentLecturer = request.user.lecturer_profile
        list_of_courses = currentLecturer.courseOffered 

        other_courses = all_courses.exclude(id__in = list_of_courses.values_list('id', flat = True))
    
        context = { 'course_form': course_form,
                   'all_semesters': semester.objects.all(),
                    'LecturerForm': LecturerForm,
                    'other_courses': other_courses
                    }
        
        return render(request, 'profile.html', context)

    

def checkDups(request, optData_id): 

    currentLecturer = request.user.lecturer_profile

    curr_optData = optData.objects.get(id = optData_id)

    #list comprehension to get a list of optMethods
    list_of_optMethods = [ method_tuple[0] for method_tuple in optData.OptimizationMethods]

    print("DEBUG 1: " , list_of_optMethods)

    #filter through all optData for similar courses and different optMethods, number shouldn't exceed 5 because there're only 5 optMethods
    list_of_dups = list(optData.objects.filter(lecturer = currentLecturer, courses = curr_optData.courses))

    #list of optData with same courses and optMethod
    optDatas_with_same_optMethod = [obj for obj in list_of_dups if obj.optMethod == curr_optData.optMethod ]

    #check list_of_dups length and content i.e optMethods
    if len(list_of_dups) == 5:
        for obj in list_of_dups:
            if obj.optMethod in list_of_optMethods:
                list_of_optMethods.remove(str(obj.optMethod))
                
        if len(list_of_optMethods) == 0: 
            return True
        else: 
            return False
    else:
        return False