import { Component } from '@angular/core';
import { environment } from '@rapydo/../environments/environment'

@Component({
  selector: 'customfooter',
  providers: [],
  templateUrl: './custom.footer.html',
})
export class CustomFooterComponent {

  public project: string;
  public version: string;

  constructor() {
    var t = environment.projectTitle;
    t = t.replace(/^'/, "");
    t = t.replace(/'$/, "");
    this.project = t;
  }

}
