import { Component, Input } from '@angular/core';
import { environment } from '@rapydo/../environments/environment';

@Component({
  selector: 'customlinks',
  providers: [],
  template: `
<ul class="navbar-nav">

  <li class='nav-item' *ngIf="user && (user.isAdmin || user.isGroupAdmin)">
    <a class='nav-link' routerLink="/app/admin/users">
      Users
    </a>
  </li>

</ul>
`,
})
export class CustomNavbarComponent {

  @Input() user: any;

  constructor() { }

}


@Component({
  selector: 'custombrand',
  providers: [],
  template: `
<a class="navbar-brand" href="" target="_blank">
    {{ myproject }}
</a>
`,
})
export class CustomBrandComponent {

  public myproject: string

  constructor() {
    var t = environment.projectTitle;
    t = t.replace(/^'/, "");
    t = t.replace(/'$/, "");
    this.myproject = t; 
  }

}
