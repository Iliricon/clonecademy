import { Component, OnInit, Input, ComponentRef, ViewChild, ViewContainerRef, ComponentFactoryResolver, ComponentFactory, EventEmitter, Output } from '@angular/core';
import { AddModuleComponent } from '../add-module/add-module.component'
import { Router, ActivatedRoute } from "@angular/router"

import { FormGroup, FormControl, Validators, FormBuilder } from '@angular/forms';

import { CourseService } from '../../../service/course.service'
import { UserService } from "../../../service/user.service"

import { ServerService } from '../../../service/server.service'
@Component({
  selector: 'app-create-course',
  templateUrl: './create-course.component.html',
  styleUrls: ['./create-course.component.scss']
})
export class CreateCourseComponent {

  @ViewChild('modules', {read: ViewContainerRef}) modules: ViewContainerRef;
  childComponent: ComponentFactory<AddModuleComponent>;
  moduleArray: ComponentRef<AddModuleComponent>[] = [];
  length: number = 0;
  error = false;

  loading = true;
  loadCourse: boolean;

  setCourseTrue(b: boolean){
    this.loadCourse = b
  }

  languages: Array<{id: string, name: string}> = [{id: "en", name: "English"}, {id: "de", name: "Deutsch"}]
  lng: string;
  categories: {};
  category: number;

  difficultys: Array<{value: number, name: string}> = [{value: 0, name: "Easy"}, {value: 1, name: "moderate"}, {value: 2, name: "difficult"}, {value: 3, name: "expert"}]
  diff: number;

  setCategory(id: number){
    this.category = id;
  }

  setLanguage(id: string){
    this.lng = id
  }

  setDifficulty(id: number){
    this.diff = id
  }

  title: string;

  setTitle(title: string){
    this.title = title;
  }

  validSave = true;

  public courseForm = new FormGroup({
    title: new FormControl("title", Validators.required),
    category: new FormControl('category', Validators.required),
  })

  @Output() emitter: EventEmitter<any> = new EventEmitter();

  ngAfterViewInit(){
    if(!this.user.isModerator()){
      //this.router.navigate(["/course/page-not-found"])
    }
    this.length = this.modules.length
  }

  constructor(
    public router: Router,
    public route: ActivatedRoute,
    public server: ServerService,
    private componentFactory: ComponentFactoryResolver,
    private course: CourseService,
    private user: UserService,
    private fb: FormBuilder,
  ) {
    this.childComponent = this.componentFactory.resolveComponentFactory(AddModuleComponent)
    this.server.get("get-course-categories/", true)
      .then(data => {
        this.categories = data;
        this.loading = false;
      })
  }

  clearModule(){
    this.modules.clear();
    this.moduleArray = [];
  }

  addModule(id?: number, title?: string, moduleDescription?: string, questions?: Array<any>){
    let moduleComponent = this.modules.createComponent(this.childComponent);
    let module = (<AddModuleComponent> moduleComponent.instance)

    module.id = id

    if(title != null){
      module.title = title
    }
    if(moduleDescription != null){
      module.learningText = moduleDescription
    }
    if(questions != null){
      for(let i = 0; i < questions.length; i++){
        let question = questions[i]
        module.editQuestion(question['type'], question['title'], question['id'], question['body'], question['question_body'], question['feedback'])
      }
    }
    this.moduleArray.push(moduleComponent)

    module.clear.subscribe((data) => {
      let moduleSingle = moduleComponent
      if(data == "remove"){
        this.moduleArray.splice(this.moduleArray.indexOf(moduleSingle), 1)
        moduleSingle.destroy();
        this.length = this.modules.length;
      }
      else if(data == "up"){
        let index = this.modules.indexOf(moduleComponent.hostView);
        let i = index - 1 > 0 ? index - 1 : 0;
        this.modules.move(moduleComponent.hostView, i);
      }
      else if(data == "down"){
        let index = this.modules.indexOf(moduleComponent.hostView);
        let i = index + 1 < this.moduleArray.length ? index + 1 : this.moduleArray.length - 1;
        this.modules.move(moduleComponent.hostView, i);
      }
    })
    this.length = this.modules.length;
  }

  removeCourse(){
    this.modules.detach(0)
  }

  save(f){
    let saveModules = this.saveModules(f)
    if(f.valid){
      let course = {name: f.value['title'], difficulty: f.value['difficulty'], language: f.value["language"], category: f.value['category'],  modules: saveModules};

      //console.log(course)
      this.uploadState(course);
    }
  }

  saveModules(form){
    let saveModules = [];
    for(let i = 0; i < this.moduleArray.length; i++){
      let module = this.moduleArray[i];
      let index = this.modules.indexOf(module.hostView);
      let m = (<AddModuleComponent> module.instance).save(form);
      m['order'] = index
      saveModules.push(m)
    }
    return saveModules
  }

  uploadState(course){
    this.server.post('courses/save', course)
    .then(data => {
      this.course.load()
      this.router.navigate(['/course'])
    }).catch(err => {
      console.log(err)
    })
  }


}
