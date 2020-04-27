import { Component, Input } from '@angular/core';
import { environment } from '@rapydo/../environments/environment';

@Component({
  selector: 'customlinks',
  providers: [],
  templateUrl: "custom.navbar.links.html"
})
export class CustomNavbarComponent {

  @Input() user: any;

  constructor() { }

}


@Component({
  selector: 'custombrand',
  providers: [],
  templateUrl: "custom.navbar.brand.html",
})
export class CustomBrandComponent {

  public project: string

  constructor() {
    var t = environment.projectTitle;
    t = t.replace(/^'/, "");
    t = t.replace(/'$/, "");
    this.project = t; 
  }

}
